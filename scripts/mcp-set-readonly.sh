#!/usr/bin/env bash
# Aplica a mitigação de "read-only real" (Exercício 2.1, risco #2) sobre as
# fontes de negócio consumidas via MCP filesystem server: docs/novatech
# (era Confluence) e data/retrieval-corpus (era Azure AI Search).
#
# O reference server @modelcontextprotocol/server-filesystem NÃO tem um modo
# --read-only por diretório: qualquer pasta passada em `args` ganha
# write_file/edit_file/move_file/create_directory. Por isso o read-only
# precisa ser reforçado no nível do sistema operacional, não só na
# configuração do MCP.
#
# Rodar a partir da raiz do repositório: ./scripts/mcp-set-readonly.sh
set -euo pipefail

for dir in docs/novatech data/retrieval-corpus; do
  if [ ! -d "$dir" ]; then
    echo "Aviso: $dir não existe, pulando." >&2
    continue
  fi
  chmod 555 "$dir"
  find "$dir" -maxdepth 1 -type f -exec chmod 444 {} +
  echo "Read-only aplicado em: $dir"
done
