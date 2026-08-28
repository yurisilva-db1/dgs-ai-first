# Exercício 2.3 — Entrega

> Entregável do Dev para o Exercício 2.3 (ver `docs/exercicio-2-3/enunciado.md`). Ferramentas usadas: **Claude**
> (chat, para definir a árvore de skills e o mapeamento de criação/consumo) + **GitHub Copilot** (simulado neste
> ambiente — mesma ressalva do Exercício 2.2: não há acesso ao Copilot real aqui; o `SKILL.md` abaixo foi gerado
> seguindo exatamente o que um prompt de Copilot receberia — o código existente em `src/shared/errors.ts` e
> `src/functions/query/handler.ts`, o `AGENTS.md` do projeto e o Anexo C).

---

## 1. Árvore de skills

O Anexo C já traz **10 skills como stubs vazios** (`skills/{foundation,domain,artifact}/*.md`). Elas cobrem bem
os 3 dos 5 tipos de artefato citados no enunciado (endpoint RAG, teste de integração, componente React), mas
**não cobrem os outros dois** ("documentação técnica de endpoints" e "specs de produto") e tratam "componentes
React" como um artefato único quando o enunciado já distingue dois padrões diferentes (card de resposta vs
formulário de feedback). Por isso a árvore abaixo **estende** o scaffold do Anexo C em vez de só preenchê-lo:
mantém as 10 skills existentes e adiciona 10 novas, todas com dono e frequência de uso reais — nenhuma foi criada
"porque a hierarquia pedia 3 níveis".

```
skills/
├── foundation/                          (convenções globais — usadas por tudo abaixo)
│   ├── error-handling.md                ★ base de todas as outras — ver §3
│   ├── logging-conventions.md
│   ├── env-config.md
│   ├── typescript-conventions.md
│   └── project-structure.md
│
├── domain/                              (padrões por camada)
│   ├── azure-functions-endpoint.md      → base de create-rag-endpoint
│   ├── azure-ai-search-integration.md   → base de create-rag-endpoint
│   ├── react-components.md              → base de create-react-card, create-feedback-form
│   ├── testing-patterns.md              → base de create-integration-test
│   ├── technical-documentation.md       → base de create-adr, create-module-readme
│   └── spec-writing-sdd.md              → base de create-spec-{requirements,plan,tasks}
│
└── artifact/                            (receitas de geração — o que o Dev/Copilot roda no dia a dia)
    ├── create-rag-endpoint.md
    ├── create-integration-test.md
    ├── create-react-card.md
    ├── create-feedback-form.md
    ├── create-adr.md
    ├── create-module-readme.md
    ├── create-spec-requirements.md
    ├── create-spec-plan.md
    └── create-spec-tasks.md
```

Cada arquivo listado acima **já existe no repositório** (`skills/**/*.md`) — os 10 herdados do Anexo C continuam
vazios (a preencher em exercícios futuros), os 10 novos têm um stub curto apontando para a tabela da seção 2, e
`skills/foundation/error-handling.md` tem o conteúdo completo pedido no item 3 do enunciado (seção 3 abaixo).

### Por que dois artefatos novos por tipo de conteúdo em vez de "documentação genérica" e "spec genérica"

- **ADR vs README de módulo** (`create-adr` / `create-module-readme`): são documentos com público e gatilho
  diferentes — ADR é uma decisão pontual e imutável depois de aceita (dono: Tech Lead), README é vivo e evolui
  com o módulo (dono: quem escreveu o código). Uma skill única "documentação técnica" teria que carregar dois
  fluxos de aprovação diferentes no mesmo arquivo.
- **`requirements.md` / `plan.md` / `tasks.md`** (`create-spec-*`): o próprio Anexo C já define que cada um tem
  um autor e um aprovador diferentes (Product Specialist → Tech Lead → Dev). Separar as skills por artefato é o
  que deixa explícito que a skill de `requirements.md` é uma skill de **produto**, não de engenharia — reforça o
  ponto do critério de avaliação sobre "visão de time".
- **Card de resposta vs formulário de feedback** (`create-react-card` / `create-feedback-form`): o enunciado já
  os cita como dois artefatos distintos ("cards de resposta, formulários de feedback") — um é
  read-only/apresentação, o outro tem validação de input e side-effect (`POST /api/feedback`). Padrões de
  código diferentes o suficiente para não caber na mesma receita.

---

## 2. Mapeamento: skill → dono → consumidor → frequência

**Papéis do projeto** (referenciados em `AGENTS.md`): Tech Lead, Product Specialist, Dev, QA, Delivery Manager.
**Agentes consumidores**: GitHub Copilot (autocomplete/chat dentro do IDE, uso tático arquivo-a-arquivo), Claude
Code (agente com acesso a MCP — repositório, git, memória — para tarefas multi-arquivo), Claude chat (revisão,
planejamento, redação de prosa fora do IDE).

### Foundation

| Skill | Quem cria | Quem consome (papel + agente) | Frequência |
|---|---|---|---|
| `error-handling` | Tech Lead | Dev, QA · Copilot, Claude Code | **Muito alta** — todo código que pode falhar (múltiplas vezes/dia) |
| `logging-conventions` | Tech Lead | Dev, QA, Delivery Manager (indireto, via runbooks) · Copilot, Claude Code | Alta — todo handler/service loga |
| `env-config` | Tech Lead | Dev · Copilot, Claude Code | Média — só ao integrar novo serviço externo |
| `typescript-conventions` | Tech Lead | Dev, QA · Copilot, Claude Code | Muito alta — todo arquivo `.ts` |
| `project-structure` | Tech Lead | Dev, Product Specialist (novo módulo de spec), Delivery Manager (planejamento por pasta) · Copilot, Claude Code | Média — na criação de módulo/endpoint/componente novo |

### Domain

| Skill | Quem cria | Quem consome (papel + agente) | Frequência |
|---|---|---|---|
| `azure-functions-endpoint` | Tech Lead | Dev, QA · Copilot, Claude Code | Alta — vários endpoints ao longo do projeto |
| `azure-ai-search-integration` | Tech Lead + Dev Sênior | Dev · Copilot, Claude Code | Média — camada de serviços RAG |
| `react-components` | Tech Lead (ou Dev front-end sênior) | Dev front-end, QA · Copilot, Claude Code | Alta — painel web tem múltiplos componentes |
| `testing-patterns` | QA (aprovado pelo Tech Lead) | Dev, QA · Copilot, Claude Code | Muito alta — todo artefato de código precisa de teste |
| `technical-documentation` | Tech Lead | Tech Lead, Dev Sênior, Product Specialist, Delivery Manager · Claude chat, Claude Code | Média — a cada decisão relevante |
| `spec-writing-sdd` | Tech Lead + Product Specialist | Product Specialist, Tech Lead, Dev, Delivery Manager · Claude chat, Claude Code | Alta — todo novo módulo (5 já mapeados no Anexo C) |

### Artifact

| Skill | Quem cria | Quem consome (papel + agente) | Frequência |
|---|---|---|---|
| `create-rag-endpoint` | Dev Sênior (autor do T1 do query endpoint) | Dev · Copilot, Claude Code | Alta — citado no enunciado como recorrente |
| `create-integration-test` | QA | Dev, QA · Copilot, Claude Code | Alta — "mesmo padrão para todos" (enunciado) |
| `create-react-card` | Dev front-end | Dev front-end · Copilot, Claude Code | Média |
| `create-feedback-form` | Dev front-end + Product Specialist (regras do que é capturado) | Dev front-end · Copilot, Claude Code | Baixa-média — poucos formulários, mas reaproveitados |
| `create-adr` | Tech Lead | Tech Lead, Dev Sênior · Claude chat, Claude Code | Baixa — só em decisão arquitetural relevante |
| `create-module-readme` | Dev (autor do módulo) | Dev, Delivery Manager (onboarding) · Claude Code | Baixa — por módulo criado |
| `create-spec-requirements` | Product Specialist | Product Specialist, Tech Lead (aprovador) · Claude chat | Média — por módulo |
| `create-spec-plan` | Tech Lead | Tech Lead, Product Specialist, Dev Sênior (aprovadores) · Claude chat | Média — por módulo |
| `create-spec-tasks` | Dev (com apoio do Copilot) | Dev, QA, Delivery Manager (acompanha progresso), Tech Lead (aprovador) · Copilot, Claude Code | Média-alta — por módulo e a cada replanning |

**Visão de time:** das 20 skills, 6 têm o **Product Specialist** ou o **Delivery Manager** como criador ou
consumidor direto (`spec-writing-sdd`, `create-spec-requirements`, `create-feedback-form`, `create-module-readme`,
`create-spec-tasks`, `technical-documentation`) — a árvore não é só "receitas para o Copilot gerar código", é
também como produto e gestão de entrega documentam decisão e acompanham progresso usando o mesmo mecanismo
(arquivo `.md` versionado) que o Dev usa para gerar endpoint.

---

## 3. SKILL.md Foundation — `error-handling`

**Por que essa é a skill Foundation "mais importante, usada por todas as outras como base"**: toda skill de
Domain que envolve código (`azure-functions-endpoint`, `azure-ai-search-integration`, `testing-patterns`,
`react-components`) e toda skill de Artifact derivada delas (`create-rag-endpoint`, `create-integration-test`,
`create-react-card`, `create-feedback-form`) lida com algo que pode falhar: uma chamada HTTP, uma integração
externa, um teste que precisa validar o shape do erro, um componente que precisa renderizar um estado de erro.
Diferente de `typescript-conventions` (também Foundation, também usada por tudo), `error-handling` já tinha
precedente real no código (`src/shared/errors.ts`, task T1 do exercício 2.2) — dava para escrever a skill como
extensão prescritiva de um padrão que já roda e passa em teste, não como regra abstrata inventada para o
exercício.

Arquivo completo: [`skills/foundation/error-handling.md`](../../skills/foundation/error-handling.md).

Conteúdo (resumo — ver arquivo para o texto integral com código):

- **Contexto**: por que múltiplos pontos de entrada (endpoints, pipeline, bot) precisam de uma taxonomia de erro
  única, e por que isso já está parcialmente implementado em `errors.ts`/`handler.ts`.
- **8 regras prescritivas**: nunca `Error` genérico, um único `try/catch` no nível do handler, `requestId`
  obrigatório, `logger` nunca `console.log`, nunca logar body/erro bruto em `info`, `UpstreamServiceError`
  dedicado para Azure OpenAI/AI Search, catch nunca vazio, erro de negócio não é bug (classe própria, não `500`).
- **Exemplos DO**: hierarquia `AppError` → `ValidationError`/`NotFoundError`/`UpstreamServiceError` com
  `statusCode` próprio; handler com catch único mapeando por `instanceof`.
- **Exemplos DON'T**: `throw new Error(string)`, try/catch por `await`, catch vazio, `console.log(request.body)`,
  `200` com erro escondido no body, validação capturada como `500`.
- **5 anti-padrões reais do Copilot** sem essa skill: try/catch por chamada em vez de um só no handler; shape de
  erro reinventado por endpoint (quebra o parser do painel web/bot); validação tratada como bug de sistema
  (polui alarme de `500`); retry sem backoff martelando a API da Azure; log do objeto de erro inteiro em `info`
  (vaza stack trace e fragmento de PII).

---

## Arquivos desta entrega

- `skills/foundation/error-handling.md` — SKILL.md completo (item 3 do enunciado).
- `skills/foundation/logging-conventions.md`, `skills/foundation/env-config.md` — stubs novos (Foundation).
- `skills/domain/technical-documentation.md`, `skills/domain/spec-writing-sdd.md` — stubs novos (Domain).
- `skills/artifact/create-feedback-form.md`, `create-adr.md`, `create-module-readme.md`,
  `create-spec-requirements.md`, `create-spec-plan.md`, `create-spec-tasks.md` — stubs novos (Artifact).
- `docs/exercicio-2-3/entrega.md` — este documento (árvore completa, mapeamento de criação/consumo).
