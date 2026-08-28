# Tasks — Query Endpoint

> Gerado a partir de `plan.md` (Exercício 2.2). Cada task é atômica: implementável e testável de forma independente,
> com um único arquivo (ou par arquivo+teste) como superfície principal de mudança.
> Estimativas: **P** (< meio dia), **M** (até 1-2 dias), **G** (mais que isso — nenhuma task aqui é G; se alguma
> virasse G, deveria ser quebrada em subtasks menores).

---

### T1 — Scaffold do endpoint HTTP + validação de input (Zod)
**Descrição:** Registrar a rota `POST /api/query` no Azure Functions v4 (`app.http`) e validar o corpo da
requisição com Zod antes de qualquer lógica de negócio. Sem busca, sem embedding, sem chamada ao modelo —
apenas parse + validação + resposta de erro padronizada. Enquanto o restante do pipeline não existe, uma
requisição válida deve retornar `501 Not Implemented` (explícito, não um crash), e uma requisição inválida
deve retornar `400` com o motivo.

**Critérios de aceite:**
- `POST /api/query` com `{ "question": "Qual o prazo de devolução?" }` retorna `501` com corpo
  `{ "error": "not_implemented", ... }` (endpoint registrado e validação passou).
- `POST /api/query` sem o campo `question` retorna `400` com `error: "invalid_request"` e `issues` detalhando
  o campo ausente (path `["question"]`).
- `POST /api/query` com `question` vazia (`""`) ou maior que o limite definido (500 caracteres) retorna `400`.
- Corpo que não é JSON válido retorna `400` (não `500`) com mensagem clara, sem vazar stack trace.
- Nenhum `console.log` no código — logging via `pino` (`shared/logger.ts`), com `requestId` (invocationId) em
  toda linha de log.
- Testes unitários cobrem: sucesso de validação, campo ausente, campo vazio, campo excedendo limite, JSON malformado.

**Dependências:** nenhuma (primeira task da spec).
**Estimativa:** P

---

### T2 — Contratos de tipos compartilhados (request/response)
**Descrição:** Definir em `shared/types.ts` os tipos `QueryRequest`, `QueryResponse` e `SourceDocument`, e o
schema Zod de saída (`queryResponseSchema`) que o endpoint deverá respeitar quando o pipeline completo existir
(T8). Não implementa lógica — apenas contrato, consumido pelas tasks seguintes.

**Critérios de aceite:**
- `QueryResponse` inclui obrigatoriamente `answer: string` e `sourceDocument: { id, title, section? }`.
- `queryResponseSchema.safeParse(fixture)` retorna `success: true` para o fixture de exemplo em
  `tests/fixtures/expected-responses.ts`.
- `queryResponseSchema.safeParse({})` retorna `success: false`.
- Tipos exportados são usados por `validator.ts` (T1) via `z.infer`, sem duplicar a definição do shape do request.

**Dependências:** T1 (para alinhar o shape do `QueryRequest` já usado na validação).
**Estimativa:** P

---

### T3 — Serviço de embedding da pergunta (Azure OpenAI)
**Descrição:** `src/services/embedding.ts` com `embedQuestion(question: string): Promise<number[]>`, chamando o
deployment de embeddings do Azure OpenAI, com retry exponential backoff (`shared/retry.ts`, reutilizável por
outras chamadas Azure) para erros transitórios (429/5xx).

**Critérios de aceite:**
- Com o client do Azure OpenAI mockado, `embedQuestion` retorna um vetor do tamanho esperado (1536 ou o
  configurado).
- Em caso de erro `429`/`503`, a função tenta novamente com backoff exponencial (testável com fake timers) até
  no máximo N tentativas (configurável), e então lança um erro tipado (`UpstreamError`) — não deixa a
  promise pendurada nem retorna `undefined`.
- Erro `400` (erro do cliente, não transitório) **não** aciona retry — falha imediatamente.

**Dependências:** T2 (usa tipos/erros compartilhados).
**Estimativa:** M

---

### T4 — Busca top-5 chunks no Azure AI Search
**Descrição:** Implementar `src/services/search.ts` → `searchChunks(embedding: number[], topK = 5): Promise<Chunk[]>`,
com retry na mesma política de T3.

**Critérios de aceite:**
- Com client mockado retornando 8 resultados, `searchChunks` retorna exatamente os 5 de maior score, ordenados
  decrescentemente.
- Índice sem resultados retorna `[]` (não lança exceção — "sem contexto" é um caso válido, tratado depois na
  montagem do prompt/resposta).
- `topK` é parametrizável e respeitado (teste com `topK=3` retorna 3 itens).

**Dependências:** T2.
**Estimativa:** M

---

### T5 — Montagem do prompt respeitando o context budget
**Descrição:** `src/services/prompt-builder.ts` → `buildPrompt(systemPrompt, chunks, question)`, respeitando o
orçamento da ADR-0002 (~4K tokens de system, ~8K de chunks). Chunks que não cabem são descartados a partir do
menor score, não truncados no meio do texto.

**Critérios de aceite:**
- Com chunks cujo total excede 8K tokens (estimativa via contagem de caracteres/4, documentada no código),
  `buildPrompt` descarta os de menor score até caber, e retorna quais chunks foram efetivamente usados (para o
  `source_document` depois).
- Com chunks vazios (`[]`), o prompt final ainda é válido (system + pergunta, instruindo o modelo a dizer que
  não há contexto disponível — alinhado ao system prompt em `prompts/system-prompt.md`: "se não souber, diga
  que não sabe").
- Teste de snapshot com um caso "golden" fixo (chunks + pergunta → prompt esperado) para pegar regressões
  silenciosas na formatação.

**Dependências:** T2, T4.
**Estimativa:** M

---

### T6 — Integração com o modelo de geração (GPT-4o) + retry
**Descrição:** `src/services/completion.ts` → `generateAnswer(prompt): Promise<{ answer: string }>`, mesma
política de retry de T3/T4, com timeout configurável.

**Critérios de aceite:**
- Client mockado retornando sucesso: `generateAnswer` retorna a string de resposta do modelo.
- Erro transitório: retry com backoff (mesmo comportamento testável de T3).
- Timeout excedido: lança `UpstreamError` com `cause` identificável (não silencioso).

**Dependências:** T5.
**Estimativa:** M

---

### T7 — Montagem da resposta final com `source_document`
**Descrição:** `src/functions/query/response-builder.ts` → `buildResponse(answer, usedChunks): QueryResponse`,
validado contra `queryResponseSchema` (T2) antes de retornar — se a resposta montada não bate com o schema,
falha explicitamente (é um bug interno, não deveria vazar pro atendente sem forma).

**Critérios de aceite:**
- Dado `answer` + chunks usados, retorna objeto que passa em `queryResponseSchema.safeParse`.
- `sourceDocument` corresponde ao chunk de maior score entre os efetivamente usados no prompt (T5), não ao
  top-1 bruto da busca (T4) — os dois podem divergir quando T5 descarta chunks.
- Lista de chunks usada vazia (nenhum contexto encontrado) produz `sourceDocument: null` e resposta ainda
  válida pelo schema (schema deve permitir `sourceDocument` nulo para esse caso).

**Dependências:** T2, T6.
**Estimativa:** P

---

### T8 — Orquestração completa no handler
**Descrição:** Ligar T3→T4→T5→T6→T7 no `queryHandler` (substitui o `501` provisório de T1 pelo fluxo real).

**Critérios de aceite:**
- Teste de integração (mocks via `msw` para Azure OpenAI e Azure AI Search) cobrindo o fluxo feliz completo:
  pergunta → embedding → busca → prompt → resposta com `source_document`, batendo com um fixture de
  `tests/fixtures/expected-responses.ts`.
- Falha em qualquer etapa upstream (embedding, busca ou geração) retorna `502 Bad Gateway` com
  `error: "upstream_error"` — nunca um `500` genérico nem um stack trace no corpo da resposta.
- Latência total do fluxo feliz (com os mocks) fica registrada num log estruturado (`duration_ms`), sem
  necessidade de tracing externo nesta task.

**Dependências:** T3, T4, T5, T6, T7.
**Estimativa:** M

---

### T9 — Testes de integração e cobertura do endpoint
**Descrição:** Suíte em `tests/integration/query.test.ts` cobrindo os cenários de T1 e T8 fim a fim, garantindo
os 80% de cobertura de linha exigidos por `vitest.config.ts`.

**Critérios de aceite:**
- `npm run test` passa com o endpoint completo (T1 + T8) coberto por casos de sucesso e de cada tipo de erro
  (`400`, `502`, JSON malformado).
- Relatório de cobertura do arquivo `src/functions/query/**` ≥ 80% linhas.

**Dependências:** T8.
**Estimativa:** P

---

## Ordem sugerida de execução

```
T1 → T2 → (T3, T4 em paralelo) → T5 → T6 → T7 → T8 → T9
```

`T3` e `T4` não dependem uma da outra (embedding e busca são serviços independentes) e podem ser feitas em
paralelo por devs diferentes assim que T2 estiver pronta.

## Escopo desta entrega (Exercício 2.2)

Apenas **T1** foi implementada nesta rodada (ver `src/functions/query/validator.ts` e
`src/functions/query/handler.ts`) — as demais ficam registradas aqui como backlog da spec, na ordem em que
devem ser puxadas nas próximas iterações.
