# SKILL: error-handling

| Campo | Valor |
|---|---|
| Nível | Foundation |
| Frase de ativação | *"Vou lançar, capturar, mapear para HTTP ou logar um erro em qualquer código do projeto (endpoint, serviço, pipeline, bot)."* |
| Dono | Tech Lead |
| Consumida por | Todo Dev, QA (para saber o que testar), e todas as skills de Domain/Artifact que envolvem código (`azure-functions-endpoint`, `azure-ai-search-integration`, `testing-patterns`, `create-rag-endpoint`, `create-integration-test`) |
| Skills relacionadas | [[logging-conventions]], [[azure-functions-endpoint]], [[azure-ai-search-integration]], [[testing-patterns]] |

---

## Contexto

O NovaTech Assistant tem **múltiplos pontos de entrada** que podem falhar de formas diferentes: endpoints HTTP
(`query`, `feedback`, `health`), o pipeline de ingestão (batch), o bot do Teams e chamadas para serviços externos
(Azure OpenAI, Azure AI Search). Cada um desses pontos hoje tende a inventar sua própria forma de tratar erro se
não houver uma convenção única — e isso quebra três coisas concretas:

1. **O painel web e o bot do Teams** esperam um contrato de erro previsível para renderizar mensagem ao atendente.
   Se cada endpoint devolve um shape de erro diferente, o card/component de erro do frontend não sabe o que ler.
2. **Os testes de integração** (`skills/domain/testing-patterns.md`) fazem assert em status HTTP + shape do body de
   erro. Inconsistência entre endpoints obriga a duplicar lógica de asserção por endpoint.
3. **Debug em produção** depende de correlação via `requestId` nos logs. Um erro capturado e logado sem esse campo
   é, na prática, não rastreável — não dá para cruzar "o atendente relatou uma falha às 14:32" com uma linha de log.

Esta é a skill Foundation mais usada pelas demais: `create-rag-endpoint.md`, `create-integration-test.md` e a
skill `azure-functions-endpoint.md` assumem que este documento já foi lido antes de gerar qualquer handler,
service ou teste. O padrão abaixo formaliza e estende o que já existe implementado em
[`src/shared/errors.ts`](../../src/shared/errors.ts) e [`src/functions/query/handler.ts`](../../src/functions/query/handler.ts)
(task T1 do query endpoint) — não é um padrão hipotético, é o que já está rodando e passando nos 14 testes de
`tests/unit/query-*.test.ts`.

---

## Regras prescritivas

1. **Nunca lance `Error` genérico ou uma string.** Toda falha esperada (validação, upstream indisponível, recurso
   não encontrado) é uma subclasse nomeada de `AppError`, com `statusCode` próprio.
2. **Um único `try/catch` no nível externo do handler.** Não envolva cada `await` individual com seu próprio
   try/catch — isso duplica a lógica de mapeamento de status e de log. O catch externo distingue `AppError`
   (mapeia para o `statusCode` da classe) de qualquer outra coisa (sempre `500`, sem vazar detalhe interno).
3. **Toda resposta de erro inclui `requestId`** (`context.invocationId` no Azure Functions). Nunca omitir — é a
   única forma de cruzar "o que o atendente viu" com "o que o log registrou".
4. **Sempre `logger` (pino), nunca `console.log`/`console.error`.** Nível `warn` para erro esperado de negócio
   (validação, not found), nível `error` só para o que caiu no catch genérico (bug real).
5. **Nunca logar o body bruto da requisição nem o objeto de erro inteiro em nível `info`.** Pode conter a pergunta
   literal do cliente/atendente (PII) ou stack trace do SDK Azure. Logue campos específicos e não sensíveis
   (ex.: `questionLength`, não `question`).
6. **Chamadas a serviços externos (Azure OpenAI, Azure AI Search) lançam `UpstreamServiceError`**, nunca deixam o
   erro nativo do SDK vazar para o handler. Isso é o que permite decidir retry-com-backoff vs falha definitiva em
   um único lugar (ver `azure-ai-search-integration.md`).
7. **`catch` nunca fica vazio e nunca engole o erro silenciosamente.** Se decidir degradar graciosamente (ex.:
   responder sem fontes quando a busca falha), isso é uma decisão de negócio que precisa ser logada em `warn` e,
   idealmente, sinalizada no response (`degraded: true`) — não um `catch { chunks = [] }` mudo.
8. **Erro de negócio não é bug.** "Documento não encontrado", "pergunta vazia" não sobem como `500`. Modele como
   classe de erro própria (`NotFoundError`, `ValidationError`) mapeada para o status HTTP correto (`404`, `400`).

---

## Exemplos concretos

### DO — hierarquia de erro tipada, extensível

```ts
// src/shared/errors.ts
import type { ZodIssue } from "zod";

export abstract class AppError extends Error {
  abstract readonly statusCode: number;
  constructor(message: string) {
    super(message);
    this.name = new.target.name;
  }
}

/** Input do usuário não passou na validação — sempre HTTP 400. */
export class ValidationError extends AppError {
  readonly statusCode = 400;
  constructor(message: string, readonly issues: ZodIssue[]) {
    super(message);
  }
}

/** Recurso de negócio não existe — sempre HTTP 404, nunca 500. */
export class NotFoundError extends AppError {
  readonly statusCode = 404;
}

/** Azure OpenAI / Azure AI Search falharam — sempre HTTP 502, nunca o erro nativo do SDK vazando. */
export class UpstreamServiceError extends AppError {
  readonly statusCode = 502;
  constructor(
    message: string,
    readonly service: "azure-openai" | "azure-ai-search",
    readonly cause: unknown,
  ) {
    super(message);
  }
}
```

### DO — um único catch no nível do handler, mapeando por tipo

```ts
// src/functions/query/handler.ts (padrão a seguir em qualquer endpoint novo)
try {
  const query = parseQueryRequest(rawBody);         // pode lançar ValidationError
  const chunks = await search(query.question);       // pode lançar UpstreamServiceError
  const answer = await complete(query.question, chunks); // idem
  return { status: 200, jsonBody: buildResponse(answer, chunks, requestId) };
} catch (err) {
  if (err instanceof AppError) {
    logger.warn({ requestId, errType: err.name, statusCode: err.statusCode }, "request.failed");
    return {
      status: err.statusCode,
      jsonBody: { error: err.name, message: err.message, requestId },
    };
  }
  logger.error({ requestId, err }, "request.unhandled_error");
  return { status: 500, jsonBody: { error: "internal_error", requestId } };
}
```

### DON'T — os erros reais que este padrão evita

```ts
// ❌ erro genérico sem taxonomia — o catch não consegue diferenciar validação de bug real
throw new Error("busca falhou");

// ❌ try/catch por chamada — duplica mapeamento de status e log em cada endpoint novo
try {
  chunks = await search(query);
} catch (e) {
  return { status: 500, jsonBody: { error: String(e) } };
}
try {
  answer = await complete(query, chunks);
} catch (e) {
  return { status: 500, jsonBody: { error: String(e) } };
}

// ❌ catch vazio — degradação silenciosa, ninguém sabe que a busca falhou
try {
  chunks = await search(query);
} catch {
  chunks = [];
}

// ❌ console.log com body inteiro — vaza pergunta do cliente/atendente nos logs
console.log("erro na busca", request.body);

// ❌ 200 com erro escondido no body — quebra o contrato HTTP, painel web não sabe que falhou
return { status: 200, jsonBody: { success: false, error: "falhou" } };

// ❌ validação de negócio tratada como bug de sistema
try {
  const query = parseQueryRequest(rawBody);
} catch {
  return { status: 500, jsonBody: { error: "internal_error" } }; // era ValidationError, deveria ser 400
}
```

---

## Anti-padrões (o que o Copilot gera, sem esta skill, com alta frequência)

1. **`try/catch` por `await` em vez de um catch único no handler.** É o padrão "óbvio" que autocomplete sugere
   linha a linha — funciona, mas duplica lógica de status/log em todo endpoint novo e diverge com o tempo.
2. **Reinventar o shape de erro por endpoint.** Sem essa skill, `feedback/handler.ts` tende a nascer com
   `{ ok: false, reason: ... }` enquanto `query/handler.ts` usa `{ error, message, requestId }` — dois endpoints,
   dois contratos, e o painel web/bot precisam de um parser de erro por endpoint.
3. **Tratar erro de validação como erro interno.** O reflexo mais comum do Copilot é `catch (err) { return { status:
   500 } }` genérico — isso transforma "atendente digitou uma pergunta vazia" em alarme de `500` no monitoramento,
   escondendo bugs reais no ruído.
4. **Retry ingênuo sem backoff em chamada de upstream.** Ao pedir "retry para a chamada da Azure OpenAI", o
   Copilot tende a gerar um `for` loop que tenta de novo imediatamente, sem exponential backoff nem limite —
   martela a API externa e pode até criar um efeito cascata de rate-limit. O padrão de retry correto vive em
   `azure-ai-search-integration.md`; esta skill só garante que a falha, quando esgota o retry, vira
   `UpstreamServiceError` — nunca o erro nativo do SDK Azure.
5. **Logar o objeto de erro inteiro em `info`.** `logger.info({ err }, "...")` parece inofensivo mas inclui stack
   trace completo e, em erros de SDK, fragmentos do payload da requisição — deveria ser `warn`/`error`, e o campo
   logado deveria ser curado (`errType`, `statusCode`), não o objeto bruto.
