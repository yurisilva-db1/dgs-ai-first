"""Ingestão: lê docs/, faz chunking por header, gera embeddings e grava no ChromaDB."""

import chromadb
from sentence_transformers import SentenceTransformer

from . import config
from .chunking import parse_document


def load_documents() -> list:
    chunks = []
    for path in sorted(config.DOCS_DIR.glob("*.md")):
        raw_text = path.read_text(encoding="utf-8")
        chunks.extend(parse_document(path.name, raw_text))
    return chunks


def build_collection(chunks, model: SentenceTransformer):
    client = chromadb.PersistentClient(path=str(config.CHROMA_DIR))

    try:
        client.delete_collection(config.COLLECTION_NAME)
    except Exception:
        pass

    collection = client.create_collection(
        name=config.COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    texts = [chunk.text for chunk in chunks]
    # Correção do problema 1: o embedding é gerado a partir do texto enriquecido
    # (prefixo doc/seção + tabelas linearizadas), mas o que fica armazenado e é
    # mostrado ao LLM (`documents=texts`) continua sendo o chunk original.
    embedding_texts = [chunk.embedding_text() for chunk in chunks]
    embeddings = model.encode(embedding_texts, show_progress_bar=False, normalize_embeddings=True)

    collection.add(
        ids=[chunk.chunk_id for chunk in chunks],
        documents=texts,
        embeddings=embeddings.tolist(),
        metadatas=[chunk.to_chroma_metadata() for chunk in chunks],
    )
    return collection


def run():
    chunks = load_documents()
    print(f"{len(chunks)} chunks extraídos de {len(list(config.DOCS_DIR.glob('*.md')))} documentos.")
    for chunk in chunks:
        print(f"  [{chunk.chunk_id}] {chunk.section_header!r} ({len(chunk.text)} chars)")

    model = SentenceTransformer(config.EMBEDDING_MODEL_NAME)
    collection = build_collection(chunks, model)
    print(f"\nColeção '{config.COLLECTION_NAME}' criada em {config.CHROMA_DIR} com {collection.count()} chunks.")


if __name__ == "__main__":
    run()
