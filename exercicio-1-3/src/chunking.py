"""Chunking dos documentos markdown da NovaTech.

Estratégia: split por headers (## e ###). Cada heading de nível 2 ou 3 abre um
novo chunk; o texto de um chunk vai até o próximo heading (de qualquer um dos
dois níveis). Isso reproduz a granularidade humana usada no Anexo B (ex.: a
fórmula do frete e a tabela de multiplicadores da mesma seção "2" viram dois
chunks separados porque a tabela mora em um "### 2.1" próprio) e nunca corta
uma tabela markdown no meio, já que a tabela inteira fica dentro do heading a
que pertence.

Chunks cujo corpo (texto após o heading) fica vazio são descartados — isso
acontece com headers "capa de seção" sem conteúdo próprio, como o
"## Perguntas selecionadas" do FAQ, que só existe para introduzir os "### Item
N" seguintes.
"""

import re
import unicodedata
from dataclasses import dataclass, field

HEADING_RE = re.compile(r"^(#{2,3})\s+(.*)$")
FRONT_MATTER_RE = re.compile(r"^\*\*(.+?):\*\*\s*(.*)$")
TITLE_RE = re.compile(r"^#\s+(.*)$")
TABLE_ROW_RE = re.compile(r"^\|(.+)\|\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\|[\s:|-]+\|\s*$")


def _slugify(text: str) -> str:
    text = text.strip().lower()
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return text.strip("_")


def linearize_markdown_tables(text: str) -> str:
    """Converte tabelas markdown em frases "Coluna: valor" (correção do
    problema 1). Uma tabela crua como "| Região | Multiplicador |\n| Sul | 1.2 |"
    embeda mal — pouco texto natural, nenhuma frase ligando o nome da região ao
    valor. Linearizada vira "Região: Sul; Multiplicador: 1.2.", que tanto o
    bi-encoder quanto o cross-encoder conseguem casar contra uma pergunta como
    "qual o multiplicador do Sul?". Usada só para enriquecer o texto de
    embedding/re-ranking — o chunk armazenado/exibido continua com a tabela
    original.
    """
    lines = text.splitlines()
    sentences = []
    i = 0
    while i < len(lines):
        if TABLE_ROW_RE.match(lines[i]) and i + 1 < len(lines) and TABLE_SEPARATOR_RE.match(lines[i + 1]):
            header = [cell.strip() for cell in lines[i].strip().strip("|").split("|")]
            j = i + 2
            while j < len(lines) and TABLE_ROW_RE.match(lines[j]):
                cells = [cell.strip() for cell in lines[j].strip().strip("|").split("|")]
                parts = [f"{h}: {c}" for h, c in zip(header, cells) if c]
                if parts:
                    sentences.append("; ".join(parts) + ".")
                j += 1
            i = j
        else:
            i += 1
    return " ".join(sentences)


def build_embedding_text(doc_title: str, section_header: str, text: str) -> str:
    """Texto enriquecido usado só para gerar embedding/score de re-ranking
    (correção do problema 1): prefixa com título do documento + seção e anexa
    as tabelas markdown linearizadas em frases. O chunk original (`text`)
    continua sendo o que é armazenado no ChromaDB e mostrado ao LLM."""
    parts = [f"{doc_title} > {section_header}", text]
    table_sentences = linearize_markdown_tables(text)
    if table_sentences:
        parts.append(table_sentences)
    return "\n\n".join(parts)


@dataclass
class DocChunk:
    chunk_id: str
    source_file: str
    doc_title: str
    section_header: str
    section_level: int
    text: str
    doc_metadata: dict = field(default_factory=dict)

    def embedding_text(self) -> str:
        return build_embedding_text(self.doc_title, self.section_header, self.text)

    def to_chroma_metadata(self) -> dict:
        meta = {
            "source_file": self.source_file,
            "doc_title": self.doc_title,
            "section_header": self.section_header,
            "section_level": self.section_level,
        }
        for key, value in self.doc_metadata.items():
            meta[f"doc_{key}"] = value
        return meta


def parse_document(source_file: str, raw_text: str) -> list[DocChunk]:
    """Extrai título, front-matter (bloco `**Campo:** valor`) e chunks por heading."""

    lines = raw_text.splitlines()

    doc_title = source_file
    doc_metadata: dict[str, str] = {}
    body_start = 0

    for i, line in enumerate(lines):
        title_match = TITLE_RE.match(line)
        if title_match:
            doc_title = title_match.group(1).strip()
            body_start = i + 1
            break

    i = body_start
    while i < len(lines):
        line = lines[i].strip()
        fm_match = FRONT_MATTER_RE.match(line)
        if fm_match:
            key = _slugify(fm_match.group(1))
            doc_metadata[key] = fm_match.group(2).strip()
            i += 1
            continue
        if line == "":
            i += 1
            continue
        if HEADING_RE.match(line):
            break
        # texto livre antes do primeiro heading (ex: aviso interno do FAQ) —
        # não vira chunk próprio, é ignorado para fins de recuperação.
        i += 1

    body_start = i

    chunks: list[DocChunk] = []
    section_index = 0
    current_heading = None
    current_level = None
    current_lines: list[str] = []

    def flush():
        nonlocal section_index
        if current_heading is None:
            return
        body = "\n".join(current_lines).strip()
        if not body:
            return
        section_index += 1
        stem = source_file.rsplit(".", 1)[0]
        chunk_id = f"{stem}::{section_index:02d}"
        full_text = f"{current_heading}\n\n{body}"
        chunks.append(
            DocChunk(
                chunk_id=chunk_id,
                source_file=source_file,
                doc_title=doc_title,
                section_header=current_heading.lstrip("#").strip(),
                section_level=current_level,
                text=full_text,
                doc_metadata=dict(doc_metadata),
            )
        )

    for line in lines[body_start:]:
        heading_match = HEADING_RE.match(line)
        if heading_match:
            flush()
            current_level = len(heading_match.group(1))
            current_heading = line.strip()
            current_lines = []
        else:
            current_lines.append(line)
    flush()

    return chunks
