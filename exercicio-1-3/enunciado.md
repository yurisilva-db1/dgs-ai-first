#### Exercício 1.3 — Construção de pipeline de RAG com ferramentas open-source

**Contexto:** O Tech Lead quer uma prova de conceito funcional do pipeline de RAG usando ferramentas gratuitas e open-source, antes de investir em licenças Azure. Você precisa construir um protótipo que ingira documentos, crie embeddings, armazene num vector store, e responda perguntas com base nos documentos.

**Ferramentas a utilizar:** Claude (chat) + GitHub Copilot

**Inputs fornecidos:**
- O cenário completo.
- Os documentos da NovaTech como arquivos individuais para ingestão (ver **Anexo A**, pasta `anexo-a-documentos-individuais/` — 5 arquivos .md, um por documento, prontos para processamento por scripts).
- Os chunks de referência (ver **Anexo B**) — use o mapa de cobertura como gabarito para validar se o pipeline recupera os chunks corretos.
- Stack sugerida (todas gratuitas/open-source):
  - **Python** como linguagem.
  - **ChromaDB** como vector store local (pip install chromadb).
  - **sentence-transformers** para embeddings open-source (pip install sentence-transformers — modelo sugerido: `all-MiniLM-L6-v2`).
  - **LangChain** ou código manual para orquestração (pip install langchain).
  - Para geração: usar o **Claude** (via chat manual, não via API) ou qualquer modelo local via **Ollama** (gratuito).
- Alternativa: se o participante preferir, pode usar outra stack free (FAISS em vez de ChromaDB, Ollama para embeddings locais, etc). O que importa é que funcione e seja gratuito.

**Tarefa:**
1. Usando o **GitHub Copilot**, implemente um pipeline de RAG mínimo com estas etapas:
   - **Ingestão:** Um script que lê os documentos do Anexo A (como texto), divide em chunks (defina a estratégia de chunking e justifique), gera embeddings, e armazena no ChromaDB.
   - **Busca:** Uma função que recebe uma pergunta, gera o embedding da pergunta, busca os N chunks mais similares no ChromaDB, e retorna os chunks com score de similaridade.
   - **Montagem de prompt:** Uma função que recebe os chunks recuperados e a pergunta, e monta o prompt completo (system prompt + chunks + pergunta) pronto para enviar ao LLM.

2. Teste o pipeline com ao menos 5 perguntas do mapa de cobertura do Anexo B. Para cada pergunta, documente: quais chunks foram recuperados, se são os chunks corretos (compare com o gabarito), e o score de similaridade.

3. Usando o **Claude** (chat), cole o prompt montado pelo pipeline e obtenha a resposta. Avalie: está correta? Citou fonte? Respeitou guardrails?

4. Identifique ao menos 2 problemas encontrados (ex: chunk errado recuperado, documento irrelevante no topo, chunking que cortou uma tabela no meio) e proponha correções.

**Entregável:** O código do pipeline (com evidência do Copilot), os resultados dos 5 testes com análise, e as propostas de correção.
