# SKILL: logging-conventions

| Campo | Valor |
|---|---|
| Nível | Foundation |
| Frase de ativação | *"Vou adicionar um log em qualquer handler, service ou pipeline do projeto."* |
| Dono | Tech Lead |
| Consumida por | Todo Dev, QA, Delivery Manager (indireto — dashboards/runbooks dependem do shape do log); todas as skills de Domain/Artifact que geram código |
| Skills relacionadas | [[error-handling]] |

> Backlog — conteúdo completo ainda não escrito (ver árvore e mapeamento em `docs/exercicio-2-3/entrega.md`).
> Extrai e generaliza o padrão já em uso em [`src/shared/logger.ts`](../../src/shared/logger.ts) (pino,
> `level: LOG_LEVEL`, nunca `console.log`) e nos logs estruturados de
> [`src/functions/query/handler.ts`](../../src/functions/query/handler.ts) (sempre com `requestId`).
