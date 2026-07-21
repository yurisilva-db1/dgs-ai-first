"""Busca: expande a pergunta, embeda, recupera candidatos no ChromaDB,
re-rankeia com cross-encoder e aplica o boost de classificação do documento.

Pipeline em 3 estágios (mais a expansão de query que roda antes de tudo):
0. Expansão de query (problema 1): resolve cidade→região (ex. "Manaus" →
   também busca por "Norte") antes de embedar/re-rankear.
1. Recall (bi-encoder): busca um pool de candidatos por similaridade cosseno —
   rápido, mas embeda pergunta e chunk separadamente, então discrimina mal
   chunks vizinhos com vocabulário parecido (problema 2) e tabelas cruas
   (problema 1). O embedding é feito sobre o texto enriquecido do chunk
   (`build_embedding_text`), não o texto cru.
2. Re-ranking (cross-encoder): recebe o par (pergunta, chunk) junto e aprende a
   relevância diretamente — muito mais discriminativo. Corrige o problema 2 (e
   ajuda o problema 1 ao usar o mesmo texto enriquecido do chunk).
3. Boost de classificação: ajusta o score final conforme o documento ser
   normativo/contratual ou informal (problema 3).
4. Corte por score mínimo (problema 4): candidatos com adjusted_score abaixo de
   config.MIN_ADJUSTED_SCORE são descartados antes do corte final em k — sem
   isso, o pipeline sempre devolveria os k mais próximos, mesmo quando nenhum é
   de fato relevante.
"""

import math
from dataclasses import dataclass
from functools import lru_cache

import chromadb
from sentence_transformers import CrossEncoder, SentenceTransformer

from . import config
from .chunking import build_embedding_text
from .entities import expand_query


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict
    similarity: float  # 1 - distância cosseno; 1.0 = idêntico (score bruto do bi-encoder, etapa 1)
    rerank_score: float  # score do cross-encoder normalizado via sigmoid, 0-1 (etapa 2)
    adjusted_score: float  # rerank_score + boost/penalidade de classificação; usado para ordenar (etapa 3)


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(config.EMBEDDING_MODEL_NAME)


@lru_cache(maxsize=1)
def _get_cross_encoder() -> CrossEncoder:
    return CrossEncoder(config.CROSS_ENCODER_MODEL_NAME)


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))
    return client.get_collection(config.COLLECTION_NAME)


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


def _classification_adjustment(metadata: dict) -> float:
    """Boost/penalidade conforme a classificação do documento (correção #3).

    Documentos normativos/contratuais recebem um pequeno boost; o FAQ (fonte
    informal, "NÃO validada por Compliance ou Operações") recebe uma pequena
    penalidade — sem isso, o FAQ frequentemente supera documentos oficiais no
    ranking para perguntas críticas (ver resultados/03-problemas-e-correcoes.md,
    problema 3).
    """
    text = f"{metadata.get('doc_classificacao', '')} {metadata.get('doc_status', '')}".lower()
    if "informal" in text:
        return -config.INFORMAL_SCORE_PENALTY
    if "normativo" in text or "contratual" in text:
        return config.NORMATIVE_SCORE_BOOST
    return 0.0


def search(question: str, k: int = config.DEFAULT_TOP_K) -> list[RetrievedChunk]:
    model = _get_model()
    collection = _get_collection()

    # Etapa 0: expande a pergunta com a região correspondente, se ela citar uma
    # cidade conhecida (problema 1) — não altera o texto mostrado ao LLM.
    expanded_question = expand_query(question)

    query_embedding = model.encode([expanded_question], normalize_embeddings=True)[0].tolist()

    # Etapa 1 (recall): pool de candidatos por similaridade bruta, maior que k
    # para a etapa 2 (re-ranking) ter margem de reordenar de verdade.
    candidate_k = min(collection.count(), k * config.RETRIEVAL_CANDIDATE_MULTIPLIER)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=candidate_k,
        include=["documents", "metadatas", "distances"],
    )

    chunk_ids = result["ids"][0]
    texts = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    # Etapa 2 (re-ranking): cross-encoder avalia cada par (pergunta, chunk)
    # diretamente, sobre o mesmo texto enriquecido usado na etapa 1 (problema 1).
    cross_encoder = _get_cross_encoder()
    pairs = [
        (expanded_question, build_embedding_text(metadata.get("doc_title", ""), metadata.get("section_header", ""), text))
        for text, metadata in zip(texts, metadatas)
    ]
    raw_rerank_scores = cross_encoder.predict(pairs)

    candidates = []
    for chunk_id, text, metadata, distance, raw_rerank in zip(
        chunk_ids, texts, metadatas, distances, raw_rerank_scores
    ):
        # collection foi criada com hnsw:space="cosine" -> distance = 1 - cos_sim
        similarity = 1.0 - distance
        rerank_score = _sigmoid(float(raw_rerank))

        # Etapa 3: boost/penalidade de classificação por cima do score re-rankeado.
        adjusted_score = rerank_score + _classification_adjustment(metadata)
        candidates.append(RetrievedChunk(chunk_id, text, metadata, similarity, rerank_score, adjusted_score))

    candidates.sort(key=lambda c: c.adjusted_score, reverse=True)

    # Etapa 4: descarta candidatos abaixo do score mínimo de relevância — pode
    # resultar em uma lista vazia (ver correção do problema 4).
    relevant = [c for c in candidates if c.adjusted_score >= config.MIN_ADJUSTED_SCORE]
    return relevant[:k]
