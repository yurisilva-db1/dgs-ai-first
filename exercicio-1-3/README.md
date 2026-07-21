# Exercício 1.3 — Pipeline de RAG open-source (NovaTech)

PoC de um pipeline de RAG 100% gratuito/open-source: ingestão de documentos → chunking → embeddings → ChromaDB → busca top-N → montagem de prompt para o Claude.

## Sobre as ferramentas usadas (nota de transparência)

O enunciado pede o uso do **GitHub Copilot** para implementar o código. Nesta sessão, quem escreveu o código foi o **Claude Code** (assistente de linha de comando da Anthropic) — não o GitHub Copilot. Optei por documentar essa substituição de ferramenta de forma explícita em vez de simular evidências do Copilot que não existiram. O papel de "Claude (chat)" pedido no passo 3 do enunciado também foi cumprido por mim (Claude), respondendo a cada prompt montado pelo pipeline como faria em uma janela de chat separada — sem nenhuma chamada programática à API da Anthropic.

## Stack

- **Python 3.12** puro, sem LangChain (orquestração manual — pipeline pequeno o bastante para manter cada etapa explícita e auditável).
- **ChromaDB** (`PersistentClient`, espaço de similaridade cosseno) como vector store local, em `chroma_db/`.
- **sentence-transformers** com `all-MiniLM-L6-v2` para embeddings (bi-encoder) e `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1` para re-ranking (multilíngue, treinado no mMARCO — gratuito/open-source).

## Estratégia de chunking

Split por headers markdown (`##` e `###`): cada heading de nível 2 ou 3 abre um novo chunk, que vai até o próximo heading. Chunks com corpo vazio (headers só de "capa de seção", como `## Perguntas selecionadas` no FAQ) são descartados.

**Justificativa:** os 5 documentos fonte já são organizados hierarquicamente por assunto, com headers bem definidos (inclusive o FAQ, que usa `### Item N — "pergunta"` para cada entrada). Splitar por header reproduz a granularidade humana usada no Anexo B (ex.: a fórmula do frete e a tabela de multiplicadores da mesma seção "2" viram chunks separados porque a tabela mora em um `### 2.1` próprio) e nunca corta uma tabela markdown no meio, já que a tabela inteira sempre fica dentro do heading a que pertence. Cada chunk carrega metadata do documento (versão, data, responsável, classificação normativo/contratual/informal), extraída do bloco `**Campo:** valor` no topo do arquivo — usada depois para os guardrails do prompt.

Resultado: **32 chunks** extraídos dos 5 documentos.

## Estrutura

```
docs/                        cópia local dos 5 documentos fonte (Anexo A)
src/
  config.py                  constantes (modelo, paths, top-k padrão)
  chunking.py                parser markdown → chunks por header + front-matter + enriquecimento p/ embedding (tabelas linearizadas)
  entities.py                dicionário cidade→região p/ expandir a query antes da busca
  ingest.py                  lê docs/, gera embeddings, popula o ChromaDB
  retrieve.py                busca em 4 estágios: expansão de query → bi-encoder (recall) → cross-encoder (re-ranking) → boost de classificação
  prompt_builder.py          system prompt com guardrails + montagem do prompt final
  cli.py                     `ingest` e `ask "<pergunta>" [--k N]`
chroma_db/                   índice persistido (gerado por ingest.py)
resultados/
  01-testes-retrieval.md     8 perguntas do Anexo B testadas: chunks recuperados, scores, comparação com o gabarito
  02-respostas-claude.md     resposta do "Claude chat" para cada prompt montado + avaliação (correta/citou fonte/guardrails)
  03-problemas-e-correcoes.md  4 problemas reais encontrados + correções propostas
```

## Como rodar

```bash
python3 -m venv .venv --without-pip   # ensurepip não estava disponível no ambiente
curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
.venv/bin/python -m pip install -r requirements.txt

.venv/bin/python -m src.ingest
.venv/bin/python -m src.cli ask "Qual o prazo de devolução?" --k 5
```

O comando `ask` imprime os chunks recuperados (com score) e o prompt final pronto para colar em um chat do Claude.

## Resultados

Testei 8 perguntas do mapa de cobertura do Anexo B (o enunciado pede ao menos 5) — detalhes completos em `resultados/`. Resumo:

- **3 de 8** perguntas tiveram retrieval correto de primeira (chunk esperado no top-5, sem ambiguidade grave).
- **5 de 8** expuseram alguma falha real de retrieval: chunk-gabarito fora do top-5 (às vezes bem fora, 11º–26º lugar), tabela de multiplicadores regionais nem aparecendo no top-10, ou fonte informal (FAQ) dominando o ranking para uma pergunta normativa/crítica.
- Em **nenhum** dos 8 casos o LLM (com o system prompt de guardrails) alucinou ou misturou versões contraditórias sem sinalizar — o ponto fraco desta PoC está no **retrieval**, não na geração.

Os 4 problemas documentados em `resultados/03-problemas-e-correcoes.md` (com causa raiz e correção proposta) são:
1. Chunks tabulares/curtos embeddam mal e somem do ranking (tabela de multiplicadores nem no top-10).
2. Chunk correto perde para chunks vizinhos do mesmo documento (mesmo vocabulário, pouca diferenciação semântica).
3. Fonte informal (FAQ) domina sobre documento normativo em pergunta crítica.
4. Ausência de corte por similaridade mínima — o pipeline sempre devolve top-k mesmo sem cobertura real.

## Correções aplicadas (as 4 estão implementadas)

O pipeline de busca hoje tem 5 estágios: **(0)** expansão de query — resolve cidade→região com uma frase natural (`entities.py`) antes de qualquer busca, correção do problema 1; **(1)** bi-encoder traz um pool de `k × 8` candidatos por similaridade cosseno sobre o texto **enriquecido** do chunk (`chunking.build_embedding_text`: prefixo doc/seção + tabelas markdown linearizadas em frases, também correção do problema 1); **(2)** um **cross-encoder** reordena esse pool avaliando cada par (pergunta, chunk enriquecido) diretamente — correção do problema 2; **(3)** um **boost/penalidade por classificação** do documento (normativo/contratual vs. informal) é aplicado por cima do score do cross-encoder — correção do problema 3; **(4)** candidatos com `adjusted_score` abaixo de `config.MIN_ADJUSTED_SCORE = 0.08` são descartados antes do corte final em k, podendo zerar a lista — correção do problema 4.

- **Correção 1 (enriquecimento + expansão de query):** ganho grande e claro em "Qual o SLA do cliente Gold?" — a tabela oficial (`SLA-2024 § 2`), que nunca tinha aparecido no top-5, sobe para o **2º lugar** assim que vira frases ("Gold: Até 2h úteis..."). Em "Frete para 600kg para Manaus?", o cosseno do chunk de multiplicadores quase dobra e ele sobe de 23º/24º para 14º/16º lugar — progresso real, mas ainda fora do top-5 (o cross-encoder mmarco dá pouco crédito à formulação "frete para Xkg para [cidade]", mesmo com a dica de região).
- **Correção 2 (cross-encoder) — o maior ganho medido:** em "Qual o prazo de devolução?", `POL-001 § 3.1` sobe do **11º para o 1º lugar**; em "Posso devolver carga perigosa?", `POL-001 § 3.2` sobe do **11º para o 1º lugar**. Também resolveu, de quebra, um efeito colateral que a correção 3 tinha introduzido sozinha (ver abaixo).
- **Correção 3 (boost de classificação) sobre o resultado já re-rankeado:** em "Posso devolver carga perigosa?", garante que a fonte normativa (POL-001) não fique atrás da fonte informal (FAQ) quando os dois têm relevância semelhante.
- **Efeito colateral real, encontrado e corrigido durante os testes:** aplicar só a correção 3 (sem cross-encoder) fazia 4 seções irrelevantes da POL-001 (boostadas só por serem de um documento "normativo") empurrarem a tabela de multiplicadores vigente (`PROC-042-v2 § 2.1`, sem boost por não ter esse rótulo no front-matter) para fora do top-5 em "Qual o multiplicador para o Sudeste?" — sobrava só a versão obsoleta (v1). Com o cross-encoder aplicado **antes** do boost, isso não acontece mais: as duas versões (v1 e v2) voltam a ocupar o 1º e 2º lugar, quase empatadas (0.652 vs 0.644), preservando a contradição de forma visível para o LLM.
- **⚠️ Duas regressões/limitações novas, reais e documentadas:** (a) em "Qual o SLA do cliente Platinum?" — um caso que antes tinha retrieval perfeito — o cross-encoder passou a dar score baixíssimo para o chunk FAQ que diz "não existe tier Platinum", mesmo com a palavra aparecendo literalmente na pergunta e no chunk (hipótese: o modelo mmarco foi treinado para reconhecer respostas factuais diretas, e "isso não existe" foge desse padrão — o teste não quebrou porque `SLA-2024 § 1` sustenta a resposta sozinho); (b) o boost fixo de +0.05 da correção 3 é aditivo, não proporcional — quando o cross-encoder já entrega um sinal fraco mas real (ex. ~0.03-0.04 para o chunk de Manaus), o boost "de graça" dado a qualquer seção de um documento normativo (mesmo com rerank ≈ 0) pode superá-lo. Não ajustei essa fórmula agora — fica como próximo passo natural (boost proporcional ao rerank_score em vez de constante).
- **Correção 4 (threshold mínimo de relevância) — a mais limpa das 4, sem regressões:** `MIN_ADJUSTED_SCORE = 0.08`, calibrado contra os 8 testes reais (pior caso coberto: 0.111 em "SLA Platinum"; melhor caso sem cobertura: ~0.051). Resultado: "Frete para 600kg para Manaus?" e "Frete para 300kg para Salvador?" — as duas perguntas do gabarito sem cobertura documental — agora retornam **0 chunks** em vez de 5 chunks fracos, e o prompt passa a incluir um aviso explícito de "nenhum trecho atingiu o score mínimo" em vez de depender só do LLM perceber sozinho. Nas outras 6 perguntas, o corte só removeu chunks de cauda longa (ruído) — nenhum chunk-gabarito foi perdido.

Detalhes completos (com números de todas as 8 perguntas, antes/depois de cada correção) em `resultados/03-problemas-e-correcoes.md`.
