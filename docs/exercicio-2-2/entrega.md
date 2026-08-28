# Exercício 2.2 — Entrega

> Entregável do Dev para o Exercício 2.2 (ver `docs/exercicio-2-2/enunciado.md`). Ferramentas usadas: Claude
> (chat, para quebrar o `plan.md` em `tasks.md` e para a revisão crítica) + GitHub Copilot (simulado neste
> ambiente — não há acesso ao Copilot real aqui; o código abaixo foi gerado seguindo exatamente os padrões que
> um prompt de Copilot receberia: `plan.md`, `AGENTS.md`/skills do projeto e a stack já presente no repo).
>
> **Ambiente:** este workspace não tem `node`/`npm` instalados por padrão (mesma situação do Exercício 2.1).
> Foi reaproveitado o binário Node 20.17.0 baixado manualmente naquele exercício (`/tmp/mcp-tools`) para
> **de fato** rodar `npm install`, `tsc -p .` e `vitest run` — o código abaixo não é apenas "parece correto",
> ele compila e os 14 testes passam neste ambiente.

---

## 1. `plan.md` → `tasks.md`

`plan.md` foi persistido em `specs/query-endpoint/plan.md` (estava vazio no repo; é o conteúdo fornecido no
enunciado). A partir dele, `specs/query-endpoint/tasks.md` quebra o plano em **9 tasks atômicas (T1–T9)**, cada
uma com ID, descrição, critérios de aceite verificáveis, dependências e estimativa P/M/G. Resumo:

| ID | Task | Depende de | Estimativa |
|----|------|-----------|------------|
| T1 | Scaffold do endpoint HTTP + validação de input (Zod) | — | P |
| T2 | Contratos de tipos compartilhados (request/response) | T1 | P |
| T3 | Serviço de embedding da pergunta (Azure OpenAI) | T2 | M |
| T4 | Busca top-5 chunks no Azure AI Search | T2 | M |
| T5 | Montagem do prompt respeitando context budget | T2, T4 | M |
| T6 | Integração com GPT-4o + retry | T5 | M |
| T7 | Montagem da resposta final com `source_document` | T2, T6 | P |
| T8 | Orquestração completa no handler | T3–T7 | M |
| T9 | Testes de integração e cobertura do endpoint | T8 | P |

Cada task isola uma única responsabilidade do pipeline descrito no `plan.md` (validação → embedding → busca →
prompt → geração → resposta), na ordem de dependência real entre elas — T3 e T4 são as únicas que podem rodar
em paralelo, já que embedding e busca não dependem uma da outra. Detalhes completos (critérios de aceite,
justificativa de cada dependência) em [`specs/query-endpoint/tasks.md`](../../specs/query-endpoint/tasks.md).

---

## 2. Implementação da primeira task (T1)

**Escopo:** `POST /api/query` registrado no Azure Functions v4, validação de input com Zod, sem lógica de
negócio ainda (busca/geração ficam para T3–T8) — requisição válida retorna `501` explícito em vez de simular
uma resposta que o pipeline ainda não sabe produzir.

Arquivos:
- [`src/functions/query/validator.ts`](../../src/functions/query/validator.ts) — schema Zod + `parseQueryRequest`.
- [`src/functions/query/handler.ts`](../../src/functions/query/handler.ts) — `app.http("query", ...)` + tratamento de erro (400 validação, 400 JSON malformado, 500 genérico).
- [`src/shared/errors.ts`](../../src/shared/errors.ts) — `ValidationError` (mapeada para 400).
- [`src/shared/logger.ts`](../../src/shared/logger.ts) — logger `pino`, usado no lugar de `console.log`.
- [`tests/unit/query-validator.test.ts`](../../tests/unit/query-validator.test.ts) e
  [`tests/unit/query-handler.test.ts`](../../tests/unit/query-handler.test.ts) — 14 casos cobrindo os critérios
  de aceite de T1.
- `package.json` — dependências reais adicionadas (`@azure/functions`, `pino`, `zod` movido para
  `dependencies`; `@types/node` como devDependency).
- `host.json` e `main` em `package.json` — ver §3.1, gap encontrado durante a revisão.

**Evidência de execução real** (não apenas leitura de código):

```
$ npm run build       # tsc -p .   → sem erros
$ npm test            # vitest run → 2 arquivos, 14 testes, todos passando
```

---

## 3. Revisão crítica do código gerado

### 3.1 [Corrigido nesta entrega] Projeto Azure Functions v4 sem `host.json` nem `main` — a função não seria descoberta em runtime

O código passa em todos os testes unitários porque os testes chamam `queryHandler` diretamente — mas o pacote
`@azure/functions` v4 depende de dois artefatos que **não existiam no repo antes desta revisão**:

1. `host.json` na raiz — obrigatório para o Functions Host saber a versão do runtime e o extension bundle.
2. O campo `"main"` em `package.json`, apontando para o output compilado (`dist/src/functions/*.js`) — é assim
   que o Functions Host v4 (modelo de programação por código, sem `function.json` por função) descobre quais
   arquivos contêm chamadas a `app.http(...)`.

Sem esses dois artefatos, `func start` (ou o deploy real) simplesmente **não encontraria a rota `/api/query`**
— um teste unitário nunca pegaria isso, porque ele importa e chama `queryHandler` diretamente, sem passar pelo
Functions Host de verdade. É exatamente o tipo de lacuna que "os testes passam" esconde e um code review real
pegaria ao tentar rodar `func start` localmente.

**Ajuste aplicado:** criado `host.json` mínimo (extension bundle 4.x) e adicionado `"main": "dist/src/functions/*.js"`
em `package.json`. Isso é infraestrutura mecânica, sem ambiguidade de negócio, por isso foi corrigido direto em
vez de só sinalizado.

### 3.2 [Sinalizado, não corrigido] Limite de 500 caracteres para `question` é um palpite do dev, sem respaldo em spec

`validator.ts` define `MAX_QUESTION_LENGTH = 500` para poder ter um critério de aceite testável ("rejeita
question acima do limite"). Só que **nada no `plan.md` ou no `requirements.md` (ainda vazio — artefato do
Product Specialist, fora do escopo deste exercício) define esse número**. O `plan.md` só fala de orçamento de
*tokens* para o prompt montado (system + chunks), não de limite de tamanho da pergunta em si.

Isso é o tipo de coisa que o Copilot (ou qualquer LLM) faz com naturalidade — precisa de um limite para o
código "parecer completo" e preenche com um valor plausível — mas que não deveria passar num code review real
sem alguém confirmar: é 500 caracteres mesmo? É um limite de negócio (evitar perguntas absurdamente longas de
um atendente) ou deveria ser derivado do budget de tokens da ADR-0002? Deixei um `TODO` explícito no código
(`validator.ts`) em vez de resolver a ambiguidade sozinho, porque essa é uma decisão de produto, não de
engenharia — resolvê-la sem validação seria exatamente o tipo de "problema inventado" que a task pede para não
fazer, só que ao contrário: inventar uma regra de negócio e escondê-la como se fosse spec.

### 3.3 [Sinalizado, não corrigido] `authLevel: "function"` compartilhado entre todos os consumidores, sem estratégia de rotação

O endpoint usa `authLevel: "function"` (uma function key estática por app). Isso é razoável como primeira
linha de defesa, mas o `plan.md` já deixa claro que este endpoint será chamado por pelo menos dois consumidores
diferentes no cenário completo (bot do Teams — `src/bot/bot.ts` — e, potencialmente, o painel web). Com uma
única key compartilhada:
- Revogar acesso de um consumidor comprometido exige rotacionar a key para **todos** os consumidores.
- Não há como saber, pelos logs, **qual** consumidor fez a chamada (a key não aparece nem deveria aparecer em
  log) — o único identificador hoje é o `requestId` (invocationId), que não distingue origem.

Não é um bug de T1 em si (a task pedia "setup do endpoint com validação", não a estratégia de auth do sistema
inteiro), mas é uma decisão de arquitetura que precisa ser tomada antes do endpoint ir para produção com mais
de um consumidor — hoje não está registrada em nenhuma ADR do projeto.

---

## Arquivos desta entrega

- `specs/query-endpoint/plan.md` — plan.md do enunciado, persistido no repo.
- `specs/query-endpoint/tasks.md` — 9 tasks atômicas (T1–T9).
- `src/functions/query/validator.ts`, `src/functions/query/handler.ts` — implementação de T1.
- `src/shared/errors.ts`, `src/shared/logger.ts` — suporte compartilhado usado por T1.
- `tests/unit/query-validator.test.ts`, `tests/unit/query-handler.test.ts` — 14 testes, todos passando.
- `host.json`, `package.json` (`main` + dependências reais) — gap de runtime encontrado e corrigido (§3.1).
- `docs/exercicio-2-2/entrega.md` — este documento.
