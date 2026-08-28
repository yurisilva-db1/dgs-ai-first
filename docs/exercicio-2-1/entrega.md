# Exercício 2.1 — Configuração e uso real de MCP servers no projeto

> Entregável do Dev para o Exercício 2.1 (ver `docs/exercicio-2-1/enunciado.md` e
> `docs/anexo-c-estrutura-repositorio.md`). Todos os servers usados são
> *reference servers* gratuitos, rodando localmente via `npx`/`uvx` — nenhum
> serviço pago ou externo foi contratado.

---

## 1. Mapeamento: necessidade → MCP server

| Necessidade do projeto | Server (reference) | O que expõe (tools/resources) | Quem consome | Pasta/escopo recebido |
|---|---|---|---|---|
| Ler e **escrever** código, specs e skills | `filesystem-workspace` | Tools de I/O de arquivo: `read_text_file`, `write_file`, `edit_file`, `list_directory`, `directory_tree`, `search_files`, `move_file`, `create_directory`, `get_file_info`, `list_allowed_directories` | Dev + Copilot (geração/edição de código, specs, skills) | `./src`, `./specs`, `./skills` |
| Ler documentação de negócio da NovaTech (era Confluence) | `filesystem-docs-novatech` | As mesmas tools acima, mas o servidor só enxerga um diretório | Product Specialist / assistente (RAG "grounding") | `./docs/novatech` (**somente leitura** — ver §2) |
| "Recuperar" chunks de retrieval (era Azure AI Search) | `filesystem-retrieval-corpus` | Idem, escopo isolado | Pipeline/assistente simulando retrieval | `./data/retrieval-corpus` (**somente leitura** — ver §2) |
| Histórico, diff e branches do repo (era GitHub) | `git` | `git_status`, `git_log`, `git_diff*`, `git_show`, `git_branch` (leitura) + `git_commit`, `git_add`, `git_reset`, `git_create_branch`, `git_checkout` (escrita — ver risco §4) | Dev / Tech Lead (auditoria de histórico, revisão de mudanças) | Repositório local (`--repository .`) |
| Glossário/linguagem ubíqua e decisões persistentes | `memory` | `create_entities`, `create_relations`, `add_observations`, `read_graph`, `search_nodes`, etc. — grafo de conhecimento local | Todos os agentes (persistência de decisões entre sessões) | Arquivo local `./.mcp/memory/memory.jsonl` (dentro do repo, não a home do usuário) |
| Explorar primitivas de MCP (tools/resources/prompts) | `everything` | Servidor de demonstração do protocolo (tools de teste, resources, prompts, sampling) | Aprendizado apenas — não faz parte do fluxo real do assistente | Nenhuma pasta (não deve rodar no dia a dia; ver risco §4) |

**Por que servers separados em vez de um único `filesystem` (como no exemplo "cru" do Anexo C)?**
O exemplo do Anexo C aponta um único server `filesystem` para `./src ./specs ./skills ./docs ./data` — isso mistura, no mesmo processo e nas mesmas permissões, pastas que o agente deve poder **escrever** (código) com pastas que são fonte de verdade de **negócio** (`docs/novatech`, `data/retrieval-corpus`) e que não deveriam ser alteráveis por um agente. Separar em três instâncias do mesmo reference server é o que permite aplicar least privilege de fato (cada instância só "vê" o que precisa, e cada uma pode ser negada/permitida independentemente no cliente MCP).

---

## 2. `.mcp/mcp.json` final e justificativa de escopo

Arquivo: [`.mcp/mcp.json`](../../.mcp/mcp.json)

```json
{
  "mcpServers": {
    "filesystem-workspace": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./src", "./specs", "./skills"]
    },
    "filesystem-docs-novatech": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./docs/novatech"]
    },
    "filesystem-retrieval-corpus": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "./data/retrieval-corpus"]
    },
    "git": {
      "command": "uvx",
      "args": ["mcp-server-git", "--repository", "."]
    },
    "memory": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-memory"],
      "env": { "MEMORY_FILE_PATH": "./.mcp/memory/memory.jsonl" }
    },
    "everything": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-everything"]
    }
  }
}
```

### Justificativa de least privilege, server a server

- **`filesystem-workspace` → `./src ./specs ./skills`**: é o mínimo necessário para o Dev/Copilot gerar código, specs (`requirements.md/plan.md/tasks.md`) e skills. Não inclui `./docs`, `./data`, `./infra`, `./prompts` nem a raiz do repo — logo não enxerga `.env`, `.git/config`, `package.json` com scripts, ou qualquer segredo eventualmente presente fora dessas três pastas.
- **`filesystem-docs-novatech` → `./docs/novatech`**: escopo de **um único diretório**, exatamente a fonte que substitui o Confluence (Anexo A). Isolar num processo próprio (em vez de juntar com `./docs` inteiro, que também tem `adr/`, `runbooks/`, `onboarding.md`) evita que o agente RAG tropece em ADRs internos ou runbooks operacionais ao "ler documentação de negócio".
- **`filesystem-retrieval-corpus` → `./data/retrieval-corpus`**: idem, isolado do resto de `./data` (caso outras pastas de dados existam no futuro) e do resto do repositório.
- **Tratamento read-only das duas fontes de leitura**: o reference server `@modelcontextprotocol/server-filesystem` (testado nesta entrega, v2026.7.10) **não tem um modo somente-leitura por diretório** — qualquer pasta passada em `args` recebe automaticamente `write_file`, `edit_file`, `move_file`, `create_directory` (confirmado lendo o `tools/list` real do servidor, ver `docs/exercicio-2-1/evidencia/01-filesystem-docs-novatech.log`). Isso significa que "escopo" (quais pastas) e "permissão de escrita" não são a mesma coisa nesse servidor — **least privilege de escopo não é suficiente**. Por isso aplicamos **read-only reforçado em duas camadas independentes**:
  1. **Sistema operacional**: `chmod 555` nas pastas e `chmod 444` nos arquivos de `docs/novatech` e `data/retrieval-corpus` (script `scripts/mcp-set-readonly.sh`). Isso faz o `write_file`/`edit_file` do MCP falhar com `EACCES`, mesmo que o agente tente — comprovado em `docs/exercicio-2-1/evidencia/02-filesystem-retrieval-corpus.log`.
  2. **Cliente MCP (Claude Code)**: `.claude/settings.json` nega explicitamente as tools de escrita desses dois servers (e as tools de escrita do `git`), via `permissions.deny`, para que a UI nem ofereça a chamada.
- **`git --repository .`**: aponta só para este repositório local (não para `/` nem para o home do usuário), suficiente para "histórico/branches" sem depender de token/conta do GitHub (o server de GitHub oficial foi arquivado e exigiria credencial externa — por isso Anexo C usa `git` + `filesystem` locais).
- **`memory` com `MEMORY_FILE_PATH` explícito**: por padrão esse server grava `memory.jsonl` dentro da própria pasta de instalação do pacote (fora do repositório, difícil de achar/versionar/apagar). Apontamos para `./.mcp/memory/memory.jsonl`, dentro do projeto, para que o grafo de decisões fique visível, seja fácil de auditar/limpar e não vaze para um diretório de cache global do usuário.
- **`everything`**: não recebe nenhuma pasta (não precisa — é só para explorar tools/resources/prompts de exemplo do protocolo) e, por ser um servidor de teste do próprio SDK, não deve ficar habilitado num ambiente de desenvolvimento "real" (ver risco §4).

---

## 3. Evidência de execução

### Ambiente

Esta máquina não tinha `node`/`npx` nem `uv`/`uvx` instalados e não há acesso root (`sudo` pede senha). Para efetivamente subir os servers, sem nenhum serviço pago/externo:

- Node 20.17.0 foi baixado (binário oficial `nodejs.org`) e extraído em `/tmp/mcp-tools` (execução local, user-space, sem `sudo`).
- `uv`/`uvx` foi instalado via `curl -LsSf https://astral.sh/uv/install.sh | sh` (instalador oficial, sem `pip`/`sudo`), em `~/.local/bin`.
- Com isso, `npx -y @modelcontextprotocol/server-filesystem …` e `uvx mcp-server-git …` — exatamente os comandos do `.mcp/mcp.json` — rodam de verdade.

Como não é possível recarregar a lista de MCP servers desta sessão do Claude Code em tempo real (isso exige reiniciar o cliente para ele ler o `.mcp.json`), a evidência abaixo foi coletada com um cliente MCP mínimo (`docs/exercicio-2-1/evidencia/mcp_client.py`) que faz exatamente o que Claude/Copilot fariam: sobe o processo do server via stdio, executa o handshake `initialize` → `notifications/initialized`, lista as tools (`tools/list`) e chama tools reais (`tools/call`) — as respostas abaixo vieram do processo real do reference server, não foram simuladas.

> Para uso contínuo real dentro do Claude Code/Copilot, basta copiar este arquivo para `.mcp.json` na raiz do repositório (nome que os clientes carregam automaticamente) e reabrir o cliente — os servers aparecerão como tools `mcp__<server>__<tool>`.

### (a) Listar e ler um documento de `docs/novatech/`

Log completo: [`docs/exercicio-2-1/evidencia/01-filesystem-docs-novatech.log`](evidencia/01-filesystem-docs-novatech.log)

- Servidor confirma o escopo restrito no próprio stderr: `allowed directories set from server args: ['.../docs/novatech']`.
- `tools/call list_directory {"path": "."}` retornou os 6 arquivos reais: `FAQ-atendimento.md`, `POL-001-politica-devolucao.md`, `PROC-042-frete-especial-v1.md`, `PROC-042-v2-frete-especial-revisado.md`, `README.md`, `SLA-2024-tabela-sla-clientes.md`.
- `tools/call read_text_file {"path": "POL-001-politica-devolucao.md"}` retornou o conteúdo integral do documento (política de devolução, seções 1–3.5).

### (b) Recuperar um chunk relevante de `data/retrieval-corpus/` para uma pergunta do domínio

Log completo: [`docs/exercicio-2-1/evidencia/02-filesystem-retrieval-corpus.log`](evidencia/02-filesystem-retrieval-corpus.log)

- `tools/call read_text_file {"path": "chunks-novatech.md"}` no server `filesystem-retrieval-corpus` retornou o corpus inteiro (Anexo B), incluindo o mapa de cobertura.
- Usando o gabarito do Anexo B para a pergunta **"Qual o prazo de devolução?"**, os chunks que devem ser recuperados são `POL-001-A` e `POL-001-B` (com `POL-001-C` como relevância menor) — ambos estão presentes no texto retornado via MCP:
  - **Chunk POL-001-A**: "O cliente pode solicitar a devolução de mercadorias em até 7 (sete) dias úteis após a data de recebimento confirmada no sistema de tracking. (...)"
  - **Chunk POL-001-B**: "As seguintes categorias de carga NÃO são elegíveis para devolução pelo processo padrão: Cargas perigosas classificadas nas classes 1 a 6 da ANTT (...)"
- **Bônus (evidência da mitigação do risco §4.2)**: uma segunda chamada, `tools/call write_file {"path": "chunks-novatech.md", "content": "TENTATIVA DE ESCRITA NAO AUTORIZADA"}`, foi **rejeitada pelo próprio sistema operacional**:
  ```
  EACCES: permission denied, open '.../data/retrieval-corpus/chunks-novatech.md....tmp'
  ```
  Isto é, mesmo o servidor MCP oferecendo a tool `write_file`, a tentativa de alterar uma fonte "read-only" falhou de verdade — a mitigação em duas camadas (§2) funciona na prática, não só no papel.

### (c) Ler o histórico do repositório via `git`

Log completo: [`docs/exercicio-2-1/evidencia/03-git.log`](evidencia/03-git.log)

- `tools/call git_log {"repo_path": ".", "max_count": 10}` retornou o commit real do branch atual: `a7abc14... "Init repo" (Yuri Silva <yuri.nascimento@db1.com.br>)`.
- `tools/call git_branch {"repo_path": ".", "branch_type": "local"}` retornou os 3 branches locais reais: `cenario-1`, `* cenario-2`, `main`.
- `tools/call git_status {"repo_path": "."}` retornou o status real de working tree (arquivos deste exercício ainda não commitados).

### Evidência complementar: escopo do server de código

Log: [`docs/exercicio-2-1/evidencia/04-filesystem-workspace.log`](evidencia/04-filesystem-workspace.log) — `list_allowed_directories` confirma que `filesystem-workspace` enxerga exatamente `./src`, `./specs`, `./skills` (nada além disso), validando o escopo do §2.

---

## 4. Riscos de segurança (setup local) e mitigações

1. **Escopo amplo de `filesystem` expõe segredos/arquivos sensíveis.** Se o server fosse configurado apontando para a raiz do repositório (ou para o `$HOME`), qualquer `.env`, chave de API commitada por engano, ou `~/.ssh` ficaria acessível via `read_text_file`/`search_files` ao agente — e, pior, editável.
   **Mitigação:** escopo por pasta funcional e nunca a raiz do projeto/home (aplicado no §2: `./src ./specs ./skills` / `./docs/novatech` / `./data/retrieval-corpus`, nunca `.`); manter `.env*` fora de qualquer pasta alcançada por um `filesystem` server; adicionar checagem de que nenhuma pasta MCP contém segredos antes de subir o server.

2. **O reference server não tem "read-only" técnico — escrita habilitada sem revisão em fontes que deveriam ser fixas.** Como mostrado no §2/§3(b), `docs/novatech` e `data/retrieval-corpus` continuam expondo `write_file`/`edit_file`/`move_file` mesmo sendo, por definição do projeto, fontes de leitura. Um agente que alucina uma "correção" poderia sobrescrever a política de devolução ou o corpus de retrieval sem nenhum humano revisar.
   **Mitigação (implementada e testada):** permissões de sistema operacional somente-leitura (`chmod 555`/`444`, script `scripts/mcp-set-readonly.sh`) — comprovadamente bloqueia a escrita com `EACCES` — combinadas com `permissions.deny` no `.claude/settings.json` para as tools de escrita desses servers, para que a negativa aconteça antes mesmo de tentar tocar o disco.

3. **Servers com escrita habilitada em código/repositório (`filesystem-workspace`, `git`) permitem alterar arquivos e até commitar/trocar de branch sem revisão humana.** O server `git` expõe `git_commit`, `git_add`, `git_reset`, `git_checkout`, `git_create_branch` — um agente poderia, por exemplo, fazer `git_checkout` para outro branch no meio de uma tarefa (perdendo o contexto do usuário) ou commitar código quebrado.
   **Mitigação:** manter o modo de permissão do cliente (Claude Code) em "perguntar" (nunca `--dangerously-skip-permissions`) para `write_file`/`edit_file` e negar por padrão `git_commit`/`git_checkout`/`git_add`/`git_reset`/`git_create_branch` no `.claude/settings.json` (aplicado no §2), exigindo aprovação humana explícita para qualquer ação que altere o estado do repositório.

4. **Supply-chain: `npx -y` e `uvx` baixam e executam código de terceiros na hora, sem pin de versão.** `npx -y @modelcontextprotocol/server-filesystem` busca a versão mais recente publicada no npm a cada execução (o mesmo vale para `uvx mcp-server-git`); um pacote comprometido ou um typosquat com nome parecido rodaria com os mesmos privilégios do processo do agente.
   **Mitigação:** fixar versão exata nos `args` (ex.: `@modelcontextprotocol/server-filesystem@<versão testada>`) em vez de sempre pegar `latest`; revisar o publisher/repositório oficial (`modelcontextprotocol/servers`) antes de trocar de pacote; nesta entrega as versões efetivamente executadas foram capturadas nos logs de evidência (`server-filesystem` v2026.7.10 via `secure-filesystem-server 0.2.0`, `mcp-server-git` v1.29.1) para rastreabilidade.

5. **`memory` persiste um grafo de texto simples, sem controle de acesso, e por padrão fora do projeto.** Decisões e observações guardadas ali podem acumular informação sensível (nomes de clientes, dados de contrato mencionados em conversas) num arquivo `.jsonl` não criptografado.
   **Mitigação:** `MEMORY_FILE_PATH` explícito dentro do repositório (`./.mcp/memory/memory.jsonl`, aplicado no §2) para que o conteúdo seja auditável e possa ser limpo/gitignorado deliberadamente; nunca instruir o agente a guardar segredos como "observação".

---

## Arquivos desta entrega

- `.mcp/mcp.json` — configuração final dos MCP servers.
- `.claude/settings.json` — deny-list de tools de escrita (least privilege no nível do cliente).
- `scripts/mcp-set-readonly.sh` — reforço de read-only no nível do SO para `docs/novatech` e `data/retrieval-corpus`.
- `docs/exercicio-2-1/evidencia/mcp_client.py` — cliente MCP mínimo usado para gerar a evidência.
- `docs/exercicio-2-1/evidencia/01-filesystem-docs-novatech.log` — evidência (a).
- `docs/exercicio-2-1/evidencia/02-filesystem-retrieval-corpus.log` — evidência (b) + teste de bloqueio de escrita.
- `docs/exercicio-2-1/evidencia/03-git.log` — evidência (c).
- `docs/exercicio-2-1/evidencia/04-filesystem-workspace.log` — evidência complementar de escopo.
