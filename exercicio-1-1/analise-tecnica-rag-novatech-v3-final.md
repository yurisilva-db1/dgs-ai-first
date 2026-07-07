# Análise Técnica — Pipeline de RAG para Assistente de IA da NovaTech (Versão Final)

**Projeto:** Assistente de IA para atendimento ao cliente (Teams + SharePoint)
**Cliente:** NovaTech (Logística, 1.200 funcionários)
**Escopo desta análise:** Desafios de ingestão por tipo de fonte, dimensionamento da base de conhecimento, orçamento de contexto e estratégia de chunking/retrieval.

**Nota de revisão (v2):** esta versão incorpora uma revisão crítica da v1. A arquitetura técnica proposta (extração estruturada, RAG híbrido, function calling para dados tabulares) permanece válida, mas a v1 tinha um viés sistemático: tratava o desafio como puramente técnico/de pipeline, subestimando (a) a incerteza real das estimativas de volume, (b) riscos de segurança e governança que não são "detalhe de implementação", e (c) a viabilidade do prazo de 3 meses para o escopo descrito. A seção 0 resume os pontos revisados; o restante do documento foi atualizado para refletir essa revisão.

**Nota de versão final (v3):** esta é a versão final do documento, incorporando o resultado da avaliação formal (Aprovado com distinção). A avaliação não identificou nenhum gap conceitual/técnico a reforçar — o conteúdo técnico das seções 0 a 7 permanece o mesmo da v2. O único gap apontado foi de **evidência do processo**: o documento não deixava rastreável o histórico real de iteração (v1 → revisão crítica → v2). O Anexo A, ao final deste documento, fecha esse gap ao registrar esse histórico de forma explícita e auditável.

---

## 0. Sumário da revisão crítica (v1 → v2)

| # | Ponto fraco identificado na v1 | Risco se não corrigido |
|---|---|---|
| 1 | Estimativa de tokens usa razão palavra/token calibrada para inglês, aplicada a texto em PT-BR | Base real pode ser 20–40% maior que o estimado, subdimensionando índice e custo |
| 2 | Estimativa de planilhas (300K tokens / 50 planilhas) é um chute sem lastro, não um cálculo | Tabelas de frete por faixa de CEP podem ter milhares de linhas cada — o volume real pode ser 5–10x maior |
| 3 | Tabelas grandes dentro de PDF tratadas só como "chunk atômico maior", sem reconhecer que são o mesmo problema das planilhas | Tabela de SLA com centenas de linhas viola limite prático de chunk e ainda assim é mal servida por busca semântica |
| 4 | Nenhuma menção a controle de acesso (ACL) do SharePoint | Indexação plana pode expor documento restrito (ex.: RH, jurídico, contratos específicos de cliente) a qualquer atendente |
| 5 | Nenhum critério de aceite / métrica de qualidade antes do go-live | Meta de "12 → 2 minutos" é declarada, mas não há como comprovar que foi atingida com qualidade aceitável, nem taxa de alucinação aceitável definida |
| 6 | Metadados resolvem *sinalização* de contradição, mas não o *processo* de resolução | Assistente perpetua e formaliza contradições existentes em vez de forçar sua resolução — risco de a NovaTech achar que "resolveu" o problema só por tê-lo tornado visível |
| 7 | Prazo de 3 meses (discovery + dev + go-live) tratado como dado fixo, não como risco | Escopo descrito (Document Intelligence, grafo de links, function calling, reranking, governança) é grande para 3 meses; risco real de atraso ou de corte de qualidade sob pressão de prazo |
| 8 | Nenhuma menção a latência ponta-a-ponta da cadeia retrieval + rerank + LLM | Meta de UX pode falhar mesmo com resposta correta, se o atendente esperar 10–15s por chamada com cliente na linha |

---

## 1. Desafios por tipo de fonte

A base documental da NovaTech combina quatro perfis de conteúdo com propriedades estruturais muito diferentes. Tratar todos com o mesmo pipeline genérico de "extrair texto → dividir em pedaços de N tokens → indexar" é a principal causa de respostas erradas em projetos de RAG corporativo. Abaixo, o desafio específico de cada fonte, seu efeito na qualidade das respostas e a estratégia de tratamento recomendada.

### 1.1 PDFs com tabelas (tabelas de SLA, regras de cálculo de frete)

**Desafio para o pipeline:**
Extratores de texto genéricos (ex.: `pdftotext`, `PyPDF2`) linearizam tabelas lendo célula por célula na ordem de leitura do PDF, destruindo a relação linha↔coluna. Uma tabela de SLA por tipo de cliente e região, por exemplo, pode virar uma sequência de números sem contexto de qual número pertence a qual cliente/região. Tabelas que atravessam quebras de página são fragmentadas em dois blocos sem cabeçalho repetido no segundo.

**Efeito na qualidade das respostas:**
O modelo recebe números "soltos" e tenta inferir a associação correta por proximidade textual — o que gera respostas numericamente plausíveis, porém erradas (ex.: informar o SLA de frete regional errado). Esse é o tipo de erro mais perigoso em RAG: a resposta "parece" correta e fundamentada, mas não é. É crítico em compliance e regras de frete, onde há impacto financeiro e contratual direto.

**Estratégia de tratamento:**
- Extração estruturada com **Azure AI Document Intelligence (Layout model)**, que preserva a estrutura de tabela como HTML/Markdown, não como texto corrido.
- Tratar cada tabela como um **chunk atômico** (não dividir no meio de uma tabela); se a tabela for grande, dividir por *grupos de linhas completas*, repetindo o cabeçalho em cada fragmento.
- Anexar metadados por chunk: título do documento, seção, número de página, data de vigência e área responsável (Operações/Compliance/Comercial) — necessário para citação de fonte e para resolver contradições (ver seção 4).
- Gerar uma **descrição textual complementar** da tabela (ex.: "Tabela de SLA por UF — Sudeste: 24h, Sul: 48h...") para melhorar o *recall* da busca vetorial, mantendo a tabela original para grounding da resposta final.

**Correção de revisão (v2):** a v1 tratava "tabela grande" apenas como um problema de tamanho de chunk (dividir em grupos de linhas). Isso é insuficiente. Uma tabela de SLA ou de regra de frete com centenas de linhas **não é conteúdo narrativo a ser recuperado por similaridade semântica — é uma tabela de lookup**, estruturalmente idêntica às planilhas de referência descritas em 1.4. Recomendação revisada: qualquer tabela dentro de PDF que exceda um limiar de linhas (ex.: >30–50 linhas) deve ser **extraída para a mesma camada estruturada/consultável das planilhas** (seção 1.4), e não apenas fragmentada em chunks de texto maiores. Só tabelas pequenas e verdadeiramente atômicas (ex.: uma tabela de 5 linhas com prazos por modalidade de frete) devem permanecer no fluxo de chunk único de RAG semântico.

### 1.2 PDFs escaneados (normas de segurança de carga, documentos mais antigos)

**Desafio para o pipeline:**
Não há camada de texto extraível — é imagem pura. Requer OCR, que introduz uma segunda fonte de erro sobre a original. Erros de OCR são particularmente danosos em números (SLA, códigos NCM, limites de peso), datas e siglas de compliance, além de normalmente perderem formatação de listas e tabelas presentes no scan.

**Efeito na qualidade das respostas:**
Erros silenciosos de OCR (ex.: "15kg" reconhecido como "75kg") produzem respostas incorretas com a mesma confiança de uma resposta correta — o assistente não tem forma de saber que errou. Documentos de segurança de carga são justamente os de maior risco regulatório/operacional se mal interpretados.

**Estratégia de tratamento:**
- OCR via **Azure AI Document Intelligence** com modelo de leitura ajustado para português, preservando layout.
- Captura do **score de confiança** por página/campo do OCR; páginas abaixo de um limiar (ex.: 85%) são marcadas para **revisão humana antes da ingestão**, não indexadas automaticamente.
- Versionamento de documento: quando uma versão digital nativa (não escaneada) do mesmo conteúdo existir ou for produzida, ela substitui a versão OCRizada no índice.
- Validação amostral periódica (ex.: 5% dos documentos escaneados) comparando OCR vs. original, para calibrar o limiar de confiança ao longo do tempo.

### 1.3 Wiki com links (Confluence, ~400 páginas)

**Desafio para o pipeline:**
Conteúdo de wiki é intrinsecamente **relacional**, não autocontido: uma página de "Política de Devolução" frequentemente diz "ver procedimento de reclamação em [link]" em vez de repetir a regra. Além disso, macros do Confluence (painéis, includes, tabelas dinâmicas) geram ruído HTML na extração, e páginas têm histórico de versões — buscar sem filtrar pode recuperar uma versão obsoleta.

**Efeito na qualidade das respostas:**
Se o retrieval traz apenas a página perguntada e não a página referenciada, o modelo responde com informação incompleta ou tenta "completar" a lacuna por conta própria — risco de alucinação por omissão de contexto. Recuperar uma versão antiga por engano reintroduz exatamente o problema de inconsistência que a NovaTech já sofre hoje.

**Estratégia de tratamento:**
- Ingestão via **API REST do Confluence** (não scraping de HTML), preservando hierarquia de espaço/página e metadados de versão/data de atualização.
- Resolver links internos **no momento da ingestão**, construindo um grafo leve de página→páginas referenciadas, permitindo *retrieval expandido*: ao recuperar uma página, trazer também o "vizinho" citado como contexto adicional (estratégia de *chunk pai/filho* aplicada à malha de links, não só à hierarquia de documento).
- Limpeza de macros/HTML para Markdown limpo antes do chunking.
- Indexar **apenas a versão vigente** por padrão, com filtro de metadado `status=atual`; versões antigas ficam acessíveis só para auditoria, não para retrieval de atendimento.

### 1.4 Planilhas com fórmulas (tabelas de referência atualizadas mensalmente)

**Desafio para o pipeline:**
RAG semântico (busca por similaridade vetorial) é um encaixe ruim para dados tabulares de lookup exato. Perguntas como "qual o prazo de entrega para o CEP X com frete Y" não são uma questão de similaridade semântica — são uma **consulta estruturada**. Além disso, extrair células de planilha como texto corrido perde a relação entre fórmula, valor calculado e cabeçalho, e a atualização mensal cria risco de a base ficar desatualizada se não houver pipeline de reingestão automática.

**Efeito na qualidade das respostas:**
Buscar por embedding em uma planilha tende a trazer linhas "parecidas" textualmente, não a linha *correta*, levando a respostas numericamente erradas em perguntas objetivas — justamente o tipo de pergunta mais comum no atendimento (prazos, valores de frete). Isso também é o cenário de maior custo de erro, pois clientes usam esses números para decisões logísticas.

**Estratégia de tratamento:**
- **Não tratar planilha como texto para RAG semântico.** Parsear com `pandas`/openpyxl, computar os valores de fórmula, e carregar em uma estrutura consultável (tabela SQL leve, ou índice estruturado do Azure AI Search com campos filtráveis).
- Expor essas tabelas ao modelo via **function calling / tool use** (o modelo decide chamar uma função de lookup com parâmetros como CEP, tipo de cliente, categoria de carga) em vez de retrieval vetorial — é uma arquitetura de *RAG agentic* combinando busca semântica (para políticas/procedimentos) com consulta estruturada (para tabelas de referência).
- Pipeline de **reingestão automática mensal** disparado por atualização do arquivo na pasta de rede (change detection por hash/data de modificação), eliminando dependência de processo manual.
- Metadado de "data de última atualização" exposto na resposta ao atendente, para transparência sobre a vigência do dado.

### 1.5 Controle de acesso (ACL) — risco transversal não tratado na v1

**Desafio para o pipeline:**
O SharePoint corporativo da NovaTech quase certamente tem documentos com permissão restrita (ex.: contratos de clientes específicos, informações de RH, auditorias internas de Compliance) misturados com documentos de uso geral. Um pipeline de RAG que indexa tudo em um único índice vetorial "achata" essas permissões: qualquer atendente que perguntar sobre o assunto pode receber, via retrieval, conteúdo de um documento ao qual não deveria ter acesso.

**Efeito na qualidade das respostas:**
Este não é um problema de qualidade de resposta — é um **incidente de segurança/vazamento de informação**, potencialmente com implicação de compliance e contratual (dados de um cliente aparecendo na resposta a outro, por exemplo). É um risco silencioso: o sistema pode funcionar "bem" tecnicamente e ainda assim causar um incidente grave.

**Estratégia de tratamento:**
- Implementar **permission trimming** no momento do retrieval: usar a identidade do usuário autenticado no Teams (via Microsoft Graph/Azure AD) para filtrar, no índice, apenas documentos aos quais aquele atendente tem acesso no SharePoint de origem — o Azure AI Search suporta filtros de segurança por identidade para este padrão.
- Mapear, no discovery, quais bibliotecas de documentos do SharePoint têm restrição de acesso hoje, e decidir explicitamente: (a) excluir essas bibliotecas da indexação, ou (b) indexar com ACL sincronizada — nunca indexar "por padrão, tudo".
- Auditoria: logar qual documento/chunk fundamentou cada resposta, para permitir investigação caso um incidente de acesso indevido seja reportado.

### Síntese comparativa

| Fonte | Principal risco | Tratamento chave |
|---|---|---|
| PDF com tabelas | Quebra da relação linha/coluna; tabelas grandes são lookup, não texto | Extração estruturada (Document Intelligence) + chunk atômico; tabelas grandes vão para camada estruturada (1.4) |
| PDF escaneado | Erro silencioso de OCR | OCR com score de confiança + revisão humana abaixo do limiar |
| Wiki com links | Contexto incompleto por referência não resolvida | Resolução de links na ingestão + retrieval expandido |
| Planilha com fórmulas | Lookup impreciso via busca semântica; volume pode ser subestimado | Function calling / consulta estruturada, não RAG vetorial |
| Todas (transversal) | Vazamento de conteúdo restrito por indexação sem ACL | Permission trimming via Azure AD/Graph no retrieval |

---

## 2. Estimativa do tamanho da base em tokens

Premissas fornecidas: regra prática de **1 token ≈ 0,75 palavras** (ou seja, `tokens = palavras / 0,75`).

**Correção de revisão (v2) — viés de idioma:** essa razão de ~0,75 palavras/token é a heurística padrão divulgada para tokenizadores da família GPT calibrados majoritariamente em **inglês**. Tokenizadores BPE tendem a fragmentar mais palavras em português — por acentuação, aglutinação e sufixos verbais (ex.: "atendimento", "responsabilidade") — resultando tipicamente em **mais tokens por palavra** do que em inglês. Na prática, é comum observar de 1,3 a 1,5 tokens por palavra em PT-BR, e não os ~1,33 implícitos na regra de 0,75 (1/0,75 = 1,33) — a diferença é pequena para essa fração específica, mas documentos com muita terminologia técnica/jurídica (comum em Compliance) tendem para o limite superior dessa faixa. Por prudência, a tabela abaixo mantém o cálculo-base pedido (0,75) e adiciona uma coluna de faixa ajustada (+15% a +30%) para refletir esse risco — a estimativa da v1 deve ser lida como **piso**, não como valor central.

| Fonte | Volume | Palavras/unidade | Total de palavras | Tokens (regra 0,75) | Tokens ajustados (PT-BR, +15–30%) |
|---|---|---|---|---|---|
| PDFs (SharePoint) | 800 docs × 10 páginas = 8.000 páginas | ~500 palavras/página (estimativa padrão para documento corporativo) | 4.000.000 | ≈ 5.333.000 | ≈ 6.130.000 – 6.930.000 |
| Wiki (Confluence) | 400 páginas | 1.500 palavras/página | 600.000 | ≈ 800.000 | ≈ 920.000 – 1.040.000 |
| Planilhas | 50 planilhas | *(ver nota — alto risco de subestimação)* | — | ≈ 300.000 | **≈ 300.000 – 2.500.000+ (ver abaixo)** |
| **Total** | | | | **≈ 6.430.000** | **≈ 7.350.000 – 10.470.000, podendo superar isso conforme as planilhas** |

**Nota sobre planilhas (revisada):** a v1 assumia ~6.000 tokens por planilha (equivalente a ~300–400 linhas de referência) sem qualquer dado de apoio — era, na prática, um chute apresentado com aparência de estimativa. Planilhas de "regras de cálculo de frete" em empresas de logística tipicamente contêm **tabelas de faixa de CEP, peso e modalidade**, que podem facilmente ter milhares de linhas por planilha. Se mesmo 10 das 50 planilhas tiverem 5.000+ linhas cada (um cenário plausível, não extremo), o volume de tokens de planilhas isoladamente pode superar 1–2 milhões de tokens — maior que o wiki inteiro. **Esta é a estimativa de maior incerteza de todo o documento e a que mais precisa de validação real no discovery antes de dimensionar a arquitetura de dados estruturados (seção 1.4).**

**Implicação central:** a base tem entre **~6,4 e ~10,5+ milhões de tokens** (podendo ser ainda maior dependendo do volume real das planilhas) — de 50x a 80x+ maior que a janela de contexto do GPT-4o (128K). A conclusão arquitetural da v1 permanece correta e fica ainda mais forte: não é viável enviar a documentação inteira em cada chamada; é obrigatório um índice vetorial/híbrido com recuperação seletiva por pergunta, complementado por consulta estruturada para dados tabulares de alto volume. Em termos de chunks de 500 tokens, isso equivale a algo entre **~12.800 e ~21.000 chunks** a serem indexados (faixa, não número fechado) — a escala que dimensiona a escolha de Azure AI Search (ou equivalente) como camada de retrieval, e que reforça a necessidade de validar o volume real de planilhas antes de comprometer uma estimativa de custo de indexação/embedding ao cliente.

---

## 3. Orçamento de contexto por query

**Dados:** janela do GPT-4o = 128.000 tokens; system prompt + instruções ≈ 2.000 tokens.

**Cálculo direto solicitado:**

```
Tokens disponíveis para contexto = 128.000 − 2.000 = 126.000 tokens
Chunks de ~500 tokens que cabem  = 126.000 / 500 ≈ 252 chunks
```

Na prática esse número já é otimista, porque ainda é preciso reservar espaço para:
- a pergunta do usuário e histórico da conversa no Teams (multi-turn) — algumas centenas a poucos milhares de tokens;
- a resposta gerada pelo modelo (recomendo reservar ~1.000–2.000 tokens de saída);
- overhead de formatação por chunk (separadores, metadados de fonte/citação, ~30–50 tokens extras por chunk).

Ajustando: **orçamento realista ≈ 120.000 tokens de contexto útil → ~230–240 chunks "cabem" fisicamente.**

**Por que isso não significa que devemos usar 230 chunks:**

Este é o ponto central da análise. Caber ≠ dever usar. Três razões práticas:

1. **Lost in the middle:** modelos de linguagem, incluindo GPT-4o, demonstram atenção degradada para informação posicionada no meio de um contexto longo, mesmo dentro da janela suportada. Preencher 230 chunks (~115K tokens) não melhora a resposta — pelo contrário, aumenta a chance de o modelo "perder" o chunk relevante entre dezenas de chunks irrelevantes, e aumenta a chance de ele misturar informação de fontes contraditórias (problema que a NovaTech já tem hoje, e que o assistente não deve reproduzir).
2. **Custo e latência:** custo e tempo de resposta em APIs de LLM escalam com tokens de entrada. Enviar 115K tokens por pergunta em um cenário de 320 chamados/dia × 60% com consulta documental (~192 consultas/dia) é ordens de magnitude mais caro e mais lento do que necessário, sem ganho de qualidade correspondente — na verdade com perda de qualidade.
3. **Precisão vs. recall:** a maioria das perguntas de atendimento ("qual o prazo para devolução de item X", "qual a regra de frete para carga perigosa") tem uma resposta fundamentada em **1 a 3 passagens específicas**, não em síntese de dezenas de documentos. Recuperar 230 chunks maximiza recall às custas de precisão — o problema não é achar informação suficiente, é achar a *certa*.

**Recomendação de orçamento prático por query:**

| Componente | Tokens reservados |
|---|---|
| System prompt + instruções | 2.000 |
| Histórico de conversa (Teams) | ~2.000–4.000 |
| Pergunta do usuário | ~100–300 |
| **Chunks recuperados (top-k após rerank)** | **~4.000–8.000** (8 a 16 chunks de ~500 tokens) |
| Resposta do modelo | ~1.500–2.000 |
| **Total usado** | **~10.000–16.000 de 128.000** |

Ou seja: o desenho correto usa **menos de 15% da janela disponível**, deliberadamente. O restante da capacidade é headroom para conversas mais longas, não para "enfiar mais documentos".

**Adição de revisão (v2) — latência ponta-a-ponta:** o orçamento de tokens acima não equivale a orçamento de tempo. A cadeia completa (busca híbrida → reranking → montagem do prompt → chamada ao LLM → formatação da resposta no Teams) tem custo de latência cumulativo que a v1 não quantificou. Uma cadeia com reranker semântico e chamada a GPT-4o tipicamente fica na faixa de 2 a 6 segundos por pergunta em condições normais — aceitável frente à meta de "menos de 2 minutos por chamado", mas **não é gratuito**: se o roteador de intenção (seção 4, item 7) acionar function calling em cascata (ex.: primeiro decide a rota, depois consulta a tabela estruturada, depois formula a resposta), a latência pode facilmente dobrar. Recomenda-se definir explicitamente uma meta de latência de resposta (ex.: p95 < 5 segundos) como critério de aceite técnico, não apenas a meta de negócio de "2 minutos por chamado", que mistura tempo de sistema com tempo de digitação/leitura do atendente.

---

## 4. Estratégia de chunking recomendada

### Por que o tamanho de chunk fixo de 500 tokens não deve ser aplicado universalmente

Um chunk de tamanho fixo funciona bem para texto narrativo (procedimentos descritos em prosa), mas quebra tabelas e listas de regras no meio — exatamente os elementos mais consultados neste projeto (SLA, regras de frete). Chunking ingênuo por contagem de tokens é a causa mais comum de respostas numericamente erradas em RAG corporativo.

### Recomendação: chunking semântico + hierárquico, não fixo

1. **Chunking por unidade lógica, com teto flexível.** Dividir por seção/cabeçalho/tabela/cláusula de política, com alvo de ~300–500 tokens para texto narrativo, mas permitindo chunks maiores (até ~1.500–2.000 tokens) quando o elemento for atômico e indivisível — uma tabela de SLA completa, por exemplo, não deve ser cortada só para caber em 500 tokens.
2. **Estratégia "small-to-big" (pai/filho):** indexar chunks pequenos (alta granularidade) para a busca vetorial, mas vincular cada um a um bloco "pai" maior (a seção completa, ou a página com a tabela inteira). Na recuperação, a busca acerta pelo chunk pequeno (melhor precisão semântica), mas o que é enviado ao modelo é o bloco pai completo — evitando o problema de uma tabela parcial ou uma regra sem seu contexto imediato.
3. **Overlap de ~10–15%** entre chunks narrativos consecutivos, para não perder contexto em fronteiras de frase/parágrafo.
4. **Metadados obrigatórios por chunk:** fonte (SharePoint/Confluence/Planilha), título do documento, seção/página/URL, data de última atualização, área responsável (Operações/Compliance/Comercial). Isso viabiliza dois requisitos explícitos da NovaTech: (a) indicação de fonte na resposta, e (b) tratamento de documentos contraditórios — o assistente pode, por exemplo, priorizar a versão de Compliance sobre Comercial em caso de conflito, ou explicitamente sinalizar "há duas versões desta regra: [fonte A, data X] diz Y; [fonte B, data Z] diz W" em vez de escolher uma silenciosamente.

**Correção de revisão (v2):** sinalizar a contradição ao atendente **não resolve o problema de origem** — apenas o torna visível mais rápido. A NovaTech já lida com contradições hoje "perguntando para quem sabe"; um assistente que apenas replica essa ambiguidade em formato de IA não entrega o valor prometido de reduzir o tempo de busca, porque o atendente ainda precisará escalar a dúvida. Recomenda-se, como entregável do projeto (não apenas do pipeline técnico), a criação de um **processo leve de governança de conteúdo**: um responsável por área (Operações/Compliance/Comercial) que recebe, semanal ou quinzenalmente, um relatório automático das contradições detectadas pelo assistente entre versões/fontes, com prazo definido para resolução na fonte. Sem esse processo, a taxa de contradição tende a se acumular, não a diminuir, à medida que a base cresce.
5. **Retrieval híbrido (vetorial + lexical/BM25) com reranking.** Perguntas de atendimento frequentemente contêm termos exatos (números de SLA, nomes de tarifas, códigos) que busca puramente semântica pode não priorizar corretamente. Um reranker (semantic ranker do Azure AI Search, por exemplo) sobre um conjunto maior recuperado por híbrido, reduzindo para o top 8–16 antes de montar o prompt, é o desenho que melhor equilibra recall e precisão dentro do orçamento de contexto calculado na seção 3.
6. **Mitigação de lost-in-the-middle na montagem do prompt:** com o conjunto final já pequeno (8–16 chunks), o risco é baixo, mas a boa prática adicional é ordenar os chunks por relevância decrescente e posicionar os mais relevantes no início e no fim do bloco de contexto (padrão em U), evitando concentrar a informação crítica no meio do prompt.
7. **Separação de rota por tipo de pergunta:** perguntas de política/procedimento (narrativas) vão para o pipeline de RAG semântico descrito acima; perguntas de lookup numérico exato (prazos por CEP, valores de frete) vão para o pipeline de function calling sobre dados estruturados (seção 1.4). Um roteador leve (classificação de intenção da pergunta) decide o caminho antes da recuperação — isso evita forçar todas as perguntas pelo mesmo funil de chunking/embedding, que é o desenho mais frágil para dados tabulares.

### Justificativa ligada ao perfil de pergunta esperado

O enunciado do projeto indica que as perguntas dos atendentes são majoritariamente objetivas e pontuais: prazos, regras de frete, políticas de devolução, procedimentos de reclamação. Esse perfil de pergunta é respondido corretamente por **poucas passagens muito relevantes**, não por síntese ampla de muitos documentos. Isso justifica um desenho que:
- prioriza precisão de retrieval (reranking, filtros de metadado, chunking que preserva tabelas) sobre volume de contexto;
- usa uma fração pequena da janela de 128K disponível, deliberadamente, para evitar degradação por lost-in-the-middle e para manter latência/custo compatíveis com a meta de reduzir o tempo de busca de 12 para menos de 2 minutos por chamado — meta que não se sustenta se cada consulta gastar 100K+ tokens e vários segundos de processamento.

---

## 5. Critérios de aceite e avaliação de qualidade (ausente na v1)

A v1 define a arquitetura de retrieval, mas não define **como medir se ela funciona** antes do go-live — uma lacuna crítica dado que os dados envolvidos (SLA, regras de frete, políticas de devolução) têm impacto financeiro e contratual direto. Recomendações:

- **Golden dataset de validação:** construir, no discovery, um conjunto de 80–150 perguntas reais (coletadas com a própria equipe de atendimento) com resposta correta e fonte esperada já conhecidas, cobrindo os quatro tipos de fonte e incluindo casos de contradição conhecida propositalmente.
- **Métricas mínimas antes do go-live:** precisão de retrieval (o chunk correto está entre os top-k recuperados?), taxa de resposta fundamentada corretamente na fonte certa, e taxa de alucinação (resposta sem suporte em nenhum chunk recuperado). Definir um limiar mínimo aceitável para cada uma (a ser acordado com a NovaTech, não definido unilateralmente pela DB1).
- **Piloto controlado:** rollout para um subconjunto da equipe (ex.: 8–10 dos 45 atendentes) antes do go-live geral, medindo tempo real de atendimento e comparando com a linha de base de 12 minutos — a meta de "<2 minutos" só deve ser declarada atingida com esse dado real, não por projeção.
- **Plano de rollback:** critério claro para pausar o assistente e voltar ao processo manual caso a taxa de erro no piloto exceda o limiar definido.

---

## 6. Risco de cronograma (3 meses discovery + dev + go-live)

A v1 tratou o prazo de 3 meses como um dado do projeto, sem avaliar se o escopo técnico descrito é compatível com ele. Ao somar o que a própria análise recomenda — extração estruturada com Document Intelligence, pipeline de OCR com revisão humana, resolução de grafo de links do Confluence, arquitetura de function calling para dados tabulares, retrieval híbrido com reranking, sincronização de ACL do SharePoint, e um golden dataset de avaliação — o escopo é considerável para 3 meses incluindo o próprio discovery.

**Riscos concretos:**
- Discovery subdimensionado (poucas semanas) tende a gerar estimativas de volume erradas (ver seção 2), descobertas tarde demais para replanejar sem atraso.
- Pressão de prazo tende a cortar exatamente os itens "invisíveis" ao cliente mas críticos: avaliação de qualidade (seção 5) e ACL (seção 1.5) são os candidatos mais prováveis a serem adiados sob pressão — e são os que geram risco reputacional/de segurança se pulados.

**Recomendação:** propor à NovaTech um **escopo de MVP faseado** dentro dos 3 meses: fase 1 cobrindo a fonte de maior volume de chamados (a definir no discovery, provavelmente SharePoint + planilhas de frete, que parecem concentrar as perguntas mais frequentes de prazo/frete) com ACL e avaliação de qualidade completas; fase 2 (pós go-live inicial) incorporando Confluence e os PDFs escaneados de menor prioridade. Isso preserva a data de go-live sem sacrificar segurança e avaliação de qualidade no que for lançado primeiro.

---

## 7. Recomendação de validação no discovery

Como diversas premissas numéricas desta análise (palavras/página real dos PDFs, tamanho real das planilhas, taxa de contradição entre documentos) são estimativas baseadas em médias declaradas pela NovaTech, recomenda-se que a fase de discovery inclua uma amostragem real de ~30–50 documentos de cada fonte para calibrar: (a) o tamanho médio de token real da base — incluindo uma amostra tokenizada de fato em PT-BR, não só a heurística de 0,75 palavras/token, (b) o tamanho real das planilhas de frete (linhas por planilha, não uma média assumida), (c) a taxa de documentos que exigem OCR vs. texto nativo, (d) a taxa de contradição efetiva entre as três áreas produtoras de conteúdo, e (e) um levantamento das bibliotecas do SharePoint com controle de acesso restrito — isso define o esforço real do pipeline de governança de conflito e de segurança antes do desenvolvimento avançar.

---

## Anexo A — Histórico de iteração do documento

Este anexo registra o processo real pelo qual esta análise foi construída, como evidência de processo (gap apontado na avaliação da v2: ausência de rastreabilidade do histórico de iteração, sem gap conceitual/técnico associado).

### A.1 Linha do tempo

| Versão | O que foi produzido | Como foi gerado | Gatilho para a próxima versão |
|---|---|---|---|
| **v1** | Documento inicial cobrindo os 4 pontos solicitados: (1) desafios de RAG por tipo de fonte (PDF com tabela, PDF escaneado, wiki com links, planilha com fórmula), (2) estimativa de tokens da base (~6,43M), (3) orçamento de contexto do GPT-4o por query, (4) estratégia de chunking justificada por perfil de pergunta e *lost in the middle*. | Resposta única a partir do contexto do cenário NovaTech fornecido, sem etapa de revisão. | Solicitação explícita de revisão crítica do próprio autor da v1, atuando como revisor. |
| **v2** | Revisão crítica estruturada da v1, com 8 pontos fracos identificados (seção 0) e correções aplicadas: viés de tokenização PT-BR (seção 2), risco de subestimação de planilhas (seção 2), tabelas grandes como problema de lookup (seção 1.1), ACL/segurança (seção 1.5 nova), QA/critério de aceite (seção 5 nova), governança como processo (seção 4, item 4), risco de cronograma de 3 meses (seção 6 nova), latência ponta-a-ponta (seção 3). | Comparação linha a linha contra a v1 (`diff -u`), com cada correção rastreada a um ponto específico de fragilidade da versão anterior. Diff unificado entregue junto ao documento. | Avaliação formal externa do documento v2. |
| **v3 (final)** | Este documento. Nenhuma mudança de conteúdo técnico em relação à v2 — a avaliação não apontou gap técnico/conceitual. Adição do presente Anexo A, registrando o histórico de iteração como evidência de processo, conforme item de melhoria da avaliação. | Incorporação do feedback de avaliação ("Aprovado com distinção"; gap de evidência de processo, não de domínio). | — (versão final para entrega). |

### A.2 Resultado da avaliação formal (v2)

- **Classificação:** Aprovado com distinção (2,5–3,0).
- **Tópicos técnicos a reforçar:** nenhum. A avaliação confirma que o conteúdo conceitual das seções 0 a 7 (desafios por fonte, dimensionamento, orçamento de contexto, chunking, segurança, QA e cronograma) está correto e completo.
- **Gap identificado:** puramente de documentação/evidência do processo de construção — a versão anterior não deixava explícito, dentro do próprio documento, o histórico real de idas e voltas entre v1 e v2. Este Anexo A fecha esse gap.

### A.3 Rastreabilidade ponto a ponto (crítica → correção)

| Ponto fraco da v1 (seção 0) | Onde foi corrigido na v2/v3 |
|---|---|
| 1. Razão palavra/token calibrada para inglês | Seção 2 — faixa ajustada PT-BR (+15–30%) |
| 2. Estimativa de planilhas sem lastro | Seção 2 — nota revisada com cenário de subestimação |
| 3. Tabela grande em PDF só como "chunk maior" | Seção 1.1 — encaminhada para camada estruturada (1.4) |
| 4. Sem controle de acesso (ACL) | Seção 1.5 (nova) |
| 5. Sem critério de aceite/QA | Seção 5 (nova) |
| 6. Governança só sinaliza, não resolve | Seção 4, item 4 — processo de governança por área |
| 7. Prazo de 3 meses não questionado | Seção 6 (nova) — recomendação de MVP faseado |
| 8. Latência ponta-a-ponta não quantificada | Seção 3 — meta de latência p95 |

Esta tabela, em conjunto com o diff unificado (`diff_v1_v2.txt`) já entregue anteriormente, constitui a evidência auditável de que cada ponto de crítica levantado foi de fato tratado na versão seguinte — e não apenas mencionado.
