"""CLI do pipeline: `ingest` para indexar os documentos, `ask` para consultar."""

import argparse

from . import config
from .ingest import run as run_ingest
from .prompt_builder import build_prompt
from .retrieve import search


def cmd_ingest(_args):
    run_ingest()


def cmd_ask(args):
    chunks = search(args.question, k=args.k)

    print(f"Pergunta: {args.question}\n")
    if chunks:
        print(f"Top-{args.k} chunks recuperados (score mínimo: {config.MIN_ADJUSTED_SCORE:.2f}):")
        for chunk in chunks:
            print(
                f"  [{chunk.chunk_id}] cosseno={chunk.similarity:.3f} rerank={chunk.rerank_score:.3f} "
                f"ajustado={chunk.adjusted_score:.3f} "
                f"— {chunk.metadata.get('doc_title')} / {chunk.metadata.get('section_header')}"
            )
        if len(chunks) < args.k:
            print(f"  (apenas {len(chunks)} de {args.k} pedidos atingiram o score mínimo de relevância)")
    else:
        print(f"Nenhum chunk atingiu o score mínimo de relevância (threshold={config.MIN_ADJUSTED_SCORE:.2f}).")

    print("\n=== PROMPT MONTADO (copiar para o Claude chat) ===\n")
    print(build_prompt(args.question, chunks))


def main():
    parser = argparse.ArgumentParser(description="Pipeline de RAG NovaTech")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("ingest", help="Processa docs/ e popula o ChromaDB").set_defaults(func=cmd_ingest)

    ask_parser = subparsers.add_parser("ask", help="Busca chunks e monta o prompt para uma pergunta")
    ask_parser.add_argument("question", help="Pergunta do atendente")
    ask_parser.add_argument("--k", type=int, default=config.DEFAULT_TOP_K, help="Número de chunks a recuperar")
    ask_parser.set_defaults(func=cmd_ask)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
