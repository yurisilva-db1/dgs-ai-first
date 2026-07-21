"""Configuração compartilhada do pipeline de RAG."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

DOCS_DIR = BASE_DIR / "docs"
CHROMA_DIR = BASE_DIR / "chroma_db"

COLLECTION_NAME = "novatech_docs"
EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"

DEFAULT_TOP_K = 5

# Etapa 1 (recall): a busca bi-encoder/cosseno traz um pool de candidatos maior
# que DEFAULT_TOP_K — esse pool é o que as correções 2 e 3 têm para reordenar
# antes do corte final. Com um corpus pequeno (32 chunks), isso na prática cobre
# quase toda a coleção, o que é intencional: dá ao cross-encoder o máximo de
# chance de recuperar um chunk correto que o bi-encoder rankeou mal.
RETRIEVAL_CANDIDATE_MULTIPLIER = 8

# Correção #2 (resultados/03-problemas-e-correcoes.md, problema 2): re-ranking
# por cross-encoder. Diferente do bi-encoder (que embeda pergunta e chunk
# separadamente e compara por cosseno), o cross-encoder recebe o par
# (pergunta, chunk) junto e aprende a relevância diretamente — discrimina muito
# melhor chunks vizinhos do mesmo documento com vocabulário parecido. Modelo
# multilíngue (inclui português, treinado no mMARCO) e gratuito/open-source.
CROSS_ENCODER_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"

# Correção #3: boost/penalidade de score aplicado conforme a classificação do
# documento (metadata doc_classificacao/doc_status), para que fontes normativas
# ou contratuais não percam sistematicamente para o FAQ informal no ranking.
# Aplicado por cima do score do cross-encoder (etapa 2), não do cosseno bruto.
NORMATIVE_SCORE_BOOST = 0.05
INFORMAL_SCORE_PENALTY = 0.05

# Correção #4 (resultados/03-problemas-e-correcoes.md, problema 4): sem corte
# de relevância mínima, o Chroma sempre devolve os k vizinhos mais próximos que
# existirem, mesmo quando nenhum é de fato relevante (ex.: pergunta sobre frete
# padrão < 500kg, tema sem cobertura na base). Calibrado empiricamente com os 8
# testes de resultados/01-testes-retrieval.md: perguntas com cobertura real
# sempre têm pelo menos 1 chunk com adjusted_score acima disto (o pior caso
# observado foi 0.111, em "SLA do cliente Platinum" — o cross-encoder pontua
# mal respostas do tipo "isso não existe", ver problema 2); perguntas sem
# cobertura real (frete abaixo de 500kg, "Manaus" sem tabela de multiplicador
# bem re-rankeada) nunca passam de ~0.051 (o piso do boost de classificação
# sobre um rerank_score perto de zero).
MIN_ADJUSTED_SCORE = 0.08
