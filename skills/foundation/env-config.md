# SKILL: env-config

| Campo | Valor |
|---|---|
| Nível | Foundation |
| Frase de ativação | *"Vou ler uma variável de ambiente ou adicionar configuração para uma nova integração externa."* |
| Dono | Tech Lead |
| Consumida por | Dev (ao integrar novo serviço Azure ou nova env var), Delivery Manager (checklist de deploy) |
| Skills relacionadas | [[azure-ai-search-integration]], [[project-structure]] |

> Backlog — conteúdo completo ainda não escrito (ver árvore e mapeamento em `docs/exercicio-2-3/entrega.md`).
> Formaliza um módulo central de config (`src/shared/config.ts`, hoje vazio) — leitura de env vars num único
> lugar, validação fail-fast na inicialização (não em runtime, no meio de uma request), nunca `process.env`
> espalhado pelo código, nunca segredo logado.
