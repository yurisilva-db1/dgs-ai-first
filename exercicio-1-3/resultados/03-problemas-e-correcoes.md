# Problemas encontrados e propostas de correção

Todos os problemas abaixo foram observados rodando o pipeline de verdade (não são hipotéticos) — ver evidência em `01-testes-retrieval.md` e `02-respostas-claude.md`.

## Problema 1 — Chunks tabulares/curtos embeddam mal e somem do ranking

**Evidência:** na pergunta 5 ("Frete para 600kg para Manaus?"), o chunk "§ 2.1 Multiplicadores regionais" — que contém a única informação capaz de responder à pergunta (a tabela de multiplicador por região) — não aparece nem entre os 10 primeiros de 32 chunks (ficou em 23º e 24º lugar, scores 0.285 e 0.282). Esse chunk é curto e quase todo tabela markdown ("| Região | Multiplicador |"), com pouco texto narrativo — o modelo `all-MiniLM-L6-v2` embeda esse tipo de conteúdo de forma genérica, sem conseguir associar "Manaus" à região "Norte".

**Causa raiz:** (a) o chunk não tem contexto textual suficiente para o embedding capturar do que se trata; (b) a pergunta usa uma cidade (Manaus) enquanto o chunk usa a região (Norte) — não há nenhuma camada de resolução geográfica.

**Correção proposta:**
1. Enriquecer o texto do chunk antes de gerar o embedding, prefixando com o título do documento e o header pai (ex.: `"PROC-042-v2 — Frete Especial > 2.1 Multiplicadores regionais (Sul, Sudeste, Centro-Oeste, Nordeste, Norte)"`), mantendo o texto original armazenado para exibição.
2. Adicionar um dicionário simples de sinônimos/entidades (cidade → região) usado para expandir a query antes do embedding (ex.: "Manaus" → adiciona "Norte" à query de busca).
3. Como alternativa mais robusta: busca híbrida (dense + BM25/keyword) para que nomes próprios curtos (regiões, siglas de documento) pesem mais que a similaridade puramente semântica.

**✅ Correções 1 e 2 implementadas.** Duas mudanças em `src/`:
- `chunking.py` (`linearize_markdown_tables` + `build_embedding_text`): antes de gerar o embedding (em `ingest.py`) e antes de montar o par para o cross-encoder (em `retrieve.py`), cada chunk é enriquecido com `"<título do doc> > <seção>"` + a tabela markdown convertida em frases `"Coluna: valor; Coluna: valor."` (ex.: `"Região: Sul; Multiplicador: 1.3."`). O texto armazenado/mostrado ao LLM (`chunk.text`, o que fica em `documents=` no Chroma) **não muda** — só o texto usado para gerar o vetor e o score de re-ranking.
- `entities.py` (novo, `expand_query`): dicionário cidade→região (Manaus→Norte, Salvador→Nordeste, etc.); se a pergunta citar uma cidade conhecida, anexa uma frase natural — `"Manaus fica na região Norte."` — ao texto usado para busca/re-ranking (a pergunta mostrada ao LLM continua a original). Testei empiricamente contra o cross-encoder: uma frase natural funciona bem melhor que uma tag `"(Região: Norte)"` entre parênteses — o modelo foi treinado em texto corrido, não em anotações estruturadas.

**Resultado observado ao re-rodar os 8 testes:**
- **Ganho grande e claro em "Qual o SLA do cliente Gold?":** a tabela oficial (`SLA-2024 § 2`, a resposta-gabarito) nunca tinha aparecido no top-5 em nenhuma versão anterior do pipeline (ficava em 7º-8º lugar). Com a tabela linearizada em frases ("Gold: Até 2h úteis; Silver: Até 4h úteis; Standard: Até 8h úteis."), ela sobe direto para o **2º lugar** (rerank=0.860) — prova de que o problema era mesmo a forma tabular, não o conteúdo.
- **Ganho parcial, mas real, em "Frete para 600kg para Manaus?":** o cosseno bruto do chunk de multiplicadores regionais salta de ~0.28 para ~0.42–0.48 (quase dobrou) e o chunk sobe de 23º/24º lugar para **14º/16º lugar** de 32 — progresso mensurável, mas ainda fora do top-5.
- **Por que "Manaus" não chega a entrar no top-5 mesmo assim:** o cross-encoder mmarco dá score baixo (~0.03–0.04) para o par (pergunta+dica de região, tabela linearizada) — bem acima do "ruído" de chunks realmente irrelevantes (~0.000-0.001), mas ainda abaixo do +0.05 que a correção 3 dá de graça para qualquer seção de um documento "normativo"/"contratual" mesmo quando o rerank dele é zero. Ou seja: a pergunta "Frete para Xkg para [cidade]?" é uma formulação bem diferente de "qual o multiplicador da região X?" (testei isoladamente: essa segunda formulação recebe um score de cross-encoder muito mais alto, ~0.83, contra a mesma tabela) — o gap final é de fraseamento entre a pergunta real do atendente e o texto da tabela, que nem o enriquecimento nem a expansão de query eliminam totalmente com este cross-encoder específico.
- **Efeito colateral pequeno e novo, também real:** para "Sudeste" (Q8), nada mudou (continua ✅, top1/top2 quase empatados). Mas para "Manaus" (Q5) o boost fixo de +0.05 da correção 3 agora compete de forma mais direta com o sinal (fraco, mas real) do cross-encoder (~0.03-0.04) para o chunk correto — um boost aditivo fixo deixa de ser proporcional quando o cross-encoder já entrega scores bem calibrados e baixos para "quase relevante". Não ajustei a fórmula do boost agora (não fazia parte do pedido desta rodada) — fica registrado como possível próximo ajuste (ex. boost proporcional ao próprio rerank_score, não uma constante).
- **Sem regressões novas** nas outras 6 perguntas — os ganhos de Q1/Q2/Q8 das correções anteriores continuam intactos.

---

## Problema 2 — Chunk correto perde para chunks vizinhos do mesmo documento

**Evidência:** na pergunta 1 ("Qual o prazo de devolução?"), a seção **3.1 "Prazo geral"** da POL-001 — a resposta direta e mais óbvia — ficou em **11º lugar** (score 0.477), atrás de seções menos relevantes do mesmo documento (3.5 Custos, 3.3 Procedimento, 3.4 Devoluções parciais). Na pergunta 2, a seção 3.2 "Exceções" (a resposta correta para "posso devolver carga perigosa") ficou em **11º lugar** também, atrás de 4 chunks do FAQ.

**Causa raiz:** chunks curtos dentro do mesmo documento normativo compartilham muito vocabulário entre si (mesmo título de documento, mesmo estilo, termos repetidos como "devolução", "dias úteis"), então o modelo de embedding tem pouca margem para diferenciá-los — pequenas variações de fraseamento da pergunta decidem o ranking de forma pouco previsível.

**Correção proposta:**
1. Adicionar uma etapa de **re-ranking**: buscar um conjunto maior de candidatos (top-15/20) por similaridade densa e depois reordenar com um cross-encoder (ou mesmo um segundo LLM de reranking) antes de cortar para o top-5 final — cross-encoders comparam pergunta+chunk diretamente e discriminam muito melhor que embeddings de frase isolados.
2. Tagging manual leve de metadata por seção (ex.: `topico: "prazo"`, `"exceção"`, `"custo"`) para permitir um boost determinístico quando um termo da pergunta bate com a tag — mitigação rápida e barata mesmo sem re-ranking.

**✅ Correção 1 implementada** em `src/retrieve.py`: pipeline agora tem 3 estágios — (1) bi-encoder traz um pool de `k × RETRIEVAL_CANDIDATE_MULTIPLIER` candidatos (multiplicador subiu de 4 para 8 para dar mais material ao re-ranking); (2) `CrossEncoder("cross-encoder/mmarco-mMiniLMv2-L12-H384-v1")` — modelo multilíngue gratuito treinado no mMARCO, que recebe cada par (pergunta, chunk) diretamente — reordena esse pool; (3) o boost de classificação (correção 3) é aplicado por cima do score do cross-encoder, não do cosseno bruto.

**Resultado observado ao re-rodar os 8 testes:**
- **Ganhos grandes e claros** nos dois casos que motivaram o problema: em "Qual o prazo de devolução?", POL-001 § 3.1 ("Prazo geral") sobe do **11º para o 1º lugar** (rerank=0.943), com § 3.3 e § 3.2 (também esperados pelo gabarito) ocupando o 2º e 3º lugar — os três chunks-gabarito da POL-001 agora dominam o top-3, e ruído (PROC-042, SLA) cai para scores de re-ranking pertinho de zero. Em "Posso devolver carga perigosa?", POL-001 § 3.2 sobe do 11º para o **1º lugar** (rerank=0.902), praticamente empatado com o FAQ (que antes dominava sozinho, 4 dos 5 chunks do top-5).
- **Resolveu o efeito colateral que a correção 3 tinha introduzido:** em "Qual o multiplicador para o Sudeste?", agora **as duas versões (v1 e v2) da tabela de multiplicadores voltam a ocupar o 1º e 2º lugar**, com scores de re-ranking quase empatados (0.652 vs 0.650) — a correção 3 sozinha tinha derrubado a v2 (vigente) para 6º lugar; com o cross-encoder no meio do caminho, o boost de classificação não tem mais chance de atropelar um chunk claramente relevante ao tópico.
- **⚠️ Regressão nova e real, descoberta ao testar:** em "Qual o SLA do cliente Platinum?" — um caso que antes tinha retrieval **perfeito** (FAQ-15 e SLA-2024 §1 no top-2) — o cross-encoder passa a dar um score baixíssimo (0.043, rank ~24 de 32) para o chunk FAQ-15 ("Não existe tier Platinum..."), mesmo a palavra "Platinum" aparecendo literalmente na pergunta e no chunk. Hipótese: o modelo mmarco foi treinado para reconhecer passagens que contêm uma resposta factual direta (estilo MS MARCO/QA), e uma resposta de "isso não existe" é um padrão diferente do que o modelo aprendeu como "relevante" — um cross-encoder genérico, fora do domínio de treino, pode falhar justamente em perguntas do tipo "isso existe?". No teste real, a resposta final não ficou incorreta porque SLA-2024 § 1 ("não existem outros tiers além dos três listados") ainda aparece no top-5 e sozinho já sustenta a resposta certa — mas é um lembrete de que um cross-encoder pronto, treinado em outro domínio/idioma-fonte, não é uma correção sem custo.
- **Confirma que o Problema 1 continua sem solução própria:** mesmo com o cross-encoder, os chunks tabulares (§ 2.1 Multiplicadores regionais para a pergunta de Manaus, § 2 Tabela de SLAs para "SLA do cliente Gold") continuam com score de re-ranking pertinho de zero (0.001–0.028) — o cross-encoder também não sabe ler uma tabela markdown crua nem resolver "Manaus → Norte". Reforça que a correção do Problema 1 (enriquecer o texto do chunk com contexto descritivo antes de indexar/re-rankear) continua necessária e é complementar a esta.

---

## Problema 3 — Fonte informal (FAQ) domina sobre documento normativo em pergunta crítica

**Evidência:** na pergunta 2 ("Posso devolver carga perigosa?"), **nenhum** chunk da POL-001 (documento normativo, "uso obrigatório pelo time de atendimento") aparece no top-5 — os 5 chunks retornados são 4 itens do FAQ (fonte explicitamente marcada como "NÃO validada por Compliance ou Operações") e 1 chunk de um documento de frete, irrelevante ao tema.

**Causa raiz:** o pipeline não diferencia a confiabilidade da fonte no momento do ranking — o score de similaridade cosseno não sabe (nem deveria saber sozinho) que um documento é normativo e outro é um FAQ informal.

**Correção proposta:**
1. Aplicar um **boost/penalidade de score por classificação do documento** já disponível na metadata (`doc_classificacao`/`doc_status`): ex. +0.03 a +0.05 para documentos "normativo"/"contratual", −0.03 a −0.05 para "informal", antes de ordenar o resultado final.
2. Alternativa mais forte: rodar duas buscas em paralelo — uma restrita a documentos formais (filtro de metadata no Chroma) e uma geral — e garantir que pelo menos 1 chunk formal apareça no contexto final sempre que existir algum acima de um piso mínimo de similaridade, mesmo que teria ficado fora do top-5 puro.
3. Isso não substitui o guardrail no system prompt (que já funcionou bem nos testes) — é uma correção complementar para reduzir a chance de o LLM nunca ver a fonte oficial.

**✅ Correção 1 implementada** em `src/retrieve.py` (`_classification_adjustment`, com pool de candidatos ampliado via `RETRIEVAL_CANDIDATE_MULTIPLIER` para o boost ter o que reordenar) — busca `+0.05` quando `doc_classificacao`/`doc_status` contém "normativo" ou "contratual", `-0.05` quando contém "informal".

**Resultado observado ao re-rodar os 8 testes com a correção ativa:**
- **Corrigiu o caso-alvo:** em "Posso devolver carga perigosa?", `POL-001 § 3.2` (a fonte normativa) sobe do 11º para o **4º lugar**, entrando no top-5 pela primeira vez.
- **Também ajudou** "Qual o prazo de devolução?" (FAQ sai do top-5, todas as 4 primeiras posições passam a ser POL-001) e "Qual o SLA do cliente Platinum?" (a tabela oficial SLA-2024 § 2 entra no top-5).
- **⚠️ Efeito colateral real (não hipotético) em "Qual o multiplicador para o Sudeste?":** o boost de +0.05 é aplicado a **todas** as seções de um documento "normativo", inclusive as irrelevantes ao tema da pergunta. Como a PROC-042 (v1 e v2) não tem o rótulo "normativo"/"contratual" no seu front-matter (só um campo "Status" descrevendo a ambiguidade de vigência — o que é, em si, um dos gaps documentados no Anexo A), suas seções não recebem boost. Resultado: 4 seções do POL-001 (irrelevantes — "Devoluções parciais", "Custos", "Objetivo") passam à frente do multiplicador da **v2** (a versão vigente), que cai do 4º para o 6º lugar — só a v1 (obsoleta) sobrevive no top-5. Ou seja, a correção 3 resolveu o problema que motivou ela (FAQ informal dominando), mas **não é gratuita**: um boost uniforme por documento, sem considerar a seção específica, pode empurrar chunks de outro documento formal, porém genuinamente mais relevantes ao tópico, para fora do top-5.
- **Diagnóstico:** esse efeito colateral é sintoma do Problema 2 (chunks curtos do mesmo/documentos correlatos competem por vocabulário parecido), não uma falha da correção 3 em si. Testei também uma variante "boost em qualquer documento não-informal" (em vez de exigir a palavra "normativo"/"contratual"), o que preserva as duas versões da PROC-042 no top-5 do teste 8 — mas aí o boost passa a valer também para as seções de "Prazo de entrega para frete especial" da PROC-042 (irrelevantes ao tema devolução), que passam a invadir o top-5 do teste 1. Não existe um ajuste de boost uniforme por documento que resolva os dois casos ao mesmo tempo — a correção completa exige o re-ranking por relevância de seção (Problema 2, cross-encoder), que o boost por classificação não substitui.

**✅ Atualização após implementar também a correção 1 do Problema 2 (cross-encoder):** o efeito colateral acima **foi resolvido**. Com o cross-encoder entrando entre a busca bruta e o boost de classificação, o score que o boost passa a ajustar já reflete relevância de seção, não só similaridade cosseno do documento inteiro — então o boost de +0.05 deixou de ser suficiente para fazer uma seção irrelevante da POL-001 (score de re-ranking pertinho de zero) ultrapassar a tabela de multiplicadores da PROC-042-v2 (score de re-ranking 0.650). Ver detalhes no Problema 2. Isso confirma o diagnóstico acima: o boost por classificação sozinho é uma correção incompleta; combinado com o re-ranking, os dois problemas (2 e 3) se resolvem juntos sem um sacrificar o outro.

---

## Problema 4 — Ausência de corte por similaridade mínima (sempre retorna top-k, mesmo sem cobertura)

**Evidência:** na pergunta 6 ("Frete para 300kg para Salvador?") — caso em que o gabarito diz explicitamente que não há chunk relevante — o pipeline ainda retornou 5 chunks "candidatos", com scores visivelmente mais baixos (0.42–0.45) que os das perguntas bem cobertas (0.5–0.7), mas sem nenhum sinal explícito de "baixa confiança" no output do `retrieve.py`/`prompt_builder.py`.

**Causa raiz:** `collection.query(n_results=k)` do ChromaDB sempre devolve os k vizinhos mais próximos existentes, independentemente de quão distantes eles estejam — não há corte de relevância configurado.

**Correção proposta:**
1. Definir um **threshold mínimo de similaridade** (ex. 0.5, calibrado empiricamente a partir da distribuição observada nestes testes) em `retrieve.py`; chunks abaixo do threshold são descartados antes de montar o prompt.
2. Se, após o corte, sobrarem zero chunks, `prompt_builder.py` deve gerar um prompt diferente, com um aviso explícito ("nenhum trecho da base atingiu o score mínimo de relevância para esta pergunta") — hoje essa detecção depende inteiramente do LLM perceber sozinho pelo conteúdo (o que funcionou nos testes 5 e 6 desta rodada, mas não é garantido).

**✅ Correção implementada** em `src/retrieve.py` + `src/config.py` + `src/prompt_builder.py`:
- `config.MIN_ADJUSTED_SCORE = 0.08` — filtra candidatos com `adjusted_score` abaixo disso, **depois** das correções 2 e 3 (cross-encoder + boost de classificação) e **antes** do corte final em k. Pode resultar em uma lista vazia.
- Threshold calibrado empiricamente contra os 8 testes reais, não escolhido a dedo: o pior caso de uma pergunta **com** cobertura real foi 0.111 (em "SLA do cliente Platinum" — mesmo com o ponto cego do cross-encoder documentado no Problema 2, o chunk correto `SLA-2024 § 1` ainda passa do threshold); o melhor caso de uma pergunta **sem** cobertura real nunca passou de ~0.051 (o piso do boost de classificação sobre um `rerank_score` perto de zero). 0.08 fica exatamente no meio desse intervalo, com folga de mais de 0.03 para os dois lados.
- `prompt_builder.py`: quando `chunks` vem vazio, o bloco de contexto do prompt deixa de ser um genérico `"(nenhum chunk recuperado)"` e passa a ser um aviso explícito (`NO_COVERAGE_NOTICE`) instruindo o LLM a não usar conhecimento geral e dizer que não encontrou a informação.
- `cli.py`: agora mostra quantos chunks pediram vs. quantos passaram no threshold (ex. "apenas 3 de 5 pedidos atingiram o score mínimo de relevância"), para transparência ao rodar o pipeline manualmente.

**Resultado observado ao re-rodar os 8 testes com o threshold ativo:**

| # | Pergunta | Chunks antes do corte (k=5) | Chunks após o corte | Resultado |
|---|---|---|---|---|
| 1 | Prazo de devolução | 5 | **3** (POL-001 §3.1, §3.3, §3.2) | mantém exatamente os 3 chunks-gabarito, descarta os 2 ruidosos |
| 2 | Carga perigosa (devolução) | 5 | **3** (POL-001 §3.2, FAQ-03, FAQ-32) | mantém os relevantes, descarta FAQ-38/POL-001-3.1 (ruído) |
| 3 | SLA Gold | 5 | **5** | bem coberta, nada descartado |
| 4 | SLA Platinum | 5 | **3** (SLA §2, §5, §1 — inclui "não existem outros tiers") | mantém a resposta certa mesmo com o ponto cego do cross-encoder |
| 5 | Frete 600kg Manaus | 5 | **0** | ✅ agora sinaliza corretamente "sem cobertura" em vez de forçar 5 chunks fracos |
| 6 | Frete 300kg Salvador | 5 | **0** | ✅ mesmo comportamento — bate exatamente com o gabarito ("nenhum chunk relevante") |
| 7 | Carga danificada | 5 | **1** (FAQ-38) | bate exatamente com o gabarito ("só FAQ-38 é fonte") |
| 8 | Multiplicador Sudeste | 5 | **2** (v1 e v2, contradição preservada) | mantém as 2 versões, descarta o resto |

Nas 8 perguntas testadas, o corte por score mínimo se comportou exatamente como o gabarito do Anexo B prevê: 2 perguntas sem cobertura real (5 e 6) agora retornam 0 chunks, e nenhuma pergunta com cobertura real perdeu o chunk certo. Esse é o resultado mais "limpo" entre as 4 correções — não introduziu nenhuma regressão nova nos 8 testes.

---

## Observação adicional (não contada como problema formal, mas documentada)

A granularidade dos meus chunks nem sempre é 1:1 com o gabarito do Anexo B: o documento fonte SLA-2024 tem "chamados gerais" e "incidentes críticos" na mesma tabela dentro de um único `## 2. Tabela de SLAs` (sem sub-header), então vira 1 chunk só, enquanto o Anexo B trata como 2 chunks lógicos (SLA-2024-B e SLA-2024-C). Isso não chega a cortar a tabela no meio — a tabela inteira permanece intacta dentro do chunk, o que é o comportamento desejado — mas é um lembrete de que "chunking por header" depende de quão bem o autor do documento organizou os headers, e nem sempre reflete a granularidade que um humano curador (Anexo B) desenhou manualmente.
