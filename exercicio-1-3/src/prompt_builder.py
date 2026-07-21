"""Montagem do prompt final (system prompt + chunks recuperados + pergunta)."""

from . import config
from .retrieve import RetrievedChunk

NO_COVERAGE_NOTICE = (
    "Nenhum trecho da base documental atingiu o score mínimo de relevância "
    f"(threshold={config.MIN_ADJUSTED_SCORE:.2f}) para esta pergunta. Isso é um forte indício "
    "de que o tema não está coberto pela base — não tente responder com base em "
    "conhecimento geral; diga ao atendente que a informação não foi encontrada na "
    "documentação da NovaTech."
)

SYSTEM_PROMPT = """Você é o assistente de atendimento da NovaTech. Responda à pergunta do \
atendente usando SOMENTE as informações presentes nos trechos de contexto abaixo.

Regras obrigatórias:
1. Não invente informação que não esteja explicitamente em algum trecho de contexto.
2. Sempre cite a fonte de cada afirmação, no formato (Fonte: <documento>, <seção>).
3. Se os trechos recuperados não contiverem a resposta, diga claramente que não \
encontrou essa informação na base documental — não tente adivinhar ou completar com \
conhecimento geral.
4. Se houver trechos de fontes classificadas como "informal" (ex.: FAQ interno, não \
validado por Compliance/Operações), você pode usá-los, mas deve avisar explicitamente \
que a informação vem de uma fonte informal/não validada, não de um documento normativo.
5. Se dois trechos contradisserem entre si (ex.: duas versões de um mesmo procedimento), \
não misture os números: aponte a contradição, indique qual trecho parece mais recente \
(pela data/versão informada) e recomende confirmar antes de aplicar."""


def _format_chunk(chunk: RetrievedChunk) -> str:
    meta = chunk.metadata
    classificacao = meta.get("doc_classificacao") or meta.get("doc_status") or "não informada"
    return (
        f"---\n"
        f"Documento: {meta.get('doc_title')} (arquivo: {meta.get('source_file')})\n"
        f"Seção: {meta.get('section_header')}\n"
        f"Versão/Data: {meta.get('doc_versao', 'n/a')} | "
        f"{meta.get('doc_data_de_emissao') or meta.get('doc_ultima_atualizacao', 'n/a')}\n"
        f"Classificação: {classificacao}\n"
        f"Score de relevância (re-ranking): {chunk.rerank_score:.3f}\n\n"
        f"{chunk.text}\n"
    )


def build_prompt(question: str, chunks: list[RetrievedChunk]) -> str:
    context_block = "\n".join(_format_chunk(c) for c in chunks) if chunks else NO_COVERAGE_NOTICE
    return (
        f"{SYSTEM_PROMPT}\n\n"
        f"=== CONTEXTO RECUPERADO ({len(chunks)} trechos) ===\n\n"
        f"{context_block}\n"
        f"=== PERGUNTA DO ATENDENTE ===\n"
        f"{question}\n"
    )
