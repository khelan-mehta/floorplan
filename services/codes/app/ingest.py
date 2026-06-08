"""Document ingestion: parse a code document and chunk it at the clause level.

Each chunk is a self-contained clause (one section number + its prose) carrying enough metadata to
serve as a citation. Chunking is by section/clause heading, NOT by fixed token windows, so a chunk
maps cleanly onto a single rule.

Parsers:
- ``.md`` / ``.txt``  — markdown/plain text headings (the seed format).
- ``.pdf``            — via PyMuPDF (optional dependency; install ``pip install '.[ingest]'``).
- ``.html`` / ``.htm``— stdlib HTML-to-text.

Section headings are detected as a leading clause number (e.g. ``1208.1``, ``Z-3.1``, ``R310.1``)
optionally preceded by markdown ``#`` markers or the word "Section".
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from .registry import SourceDoc

# A clause/section number: digits/letters with dotted parts, e.g. 1208.1, R310.1, Z-3.1, 1010.1.1
_SECTION_RE = re.compile(
    r"^\s*(?:#{1,6}\s*)?(?:Section\s+)?"
    r"(?P<section>(?:[A-Z]-?)?\d+(?:\.\d+)*)\s+"
    r"(?P<title>\S.*\S|\S)\s*$"
)
_CHAPTER_RE = re.compile(r"^\s*#{1,6}\s*(?:Chapter|Part)\b.*$", re.IGNORECASE)


@dataclass
class Chunk:
    id: str
    jurisdiction_id: str
    doc_id: str
    doc_short_code: str
    chapter: str
    section: str
    heading: str
    text: str

    def citation(self) -> dict[str, str]:
        return {"doc": self.doc_short_code, "section": self.section, "text": self.text}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        self.parts.append(data)

    def text(self) -> str:
        return "".join(self.parts)


def _read_document(doc: SourceDoc) -> str:
    path = doc.resolve()
    suffix = path.suffix.lower()
    if suffix in (".md", ".txt"):
        return path.read_text(encoding="utf-8")
    if suffix in (".html", ".htm"):
        parser = _TextExtractor()
        parser.feed(path.read_text(encoding="utf-8"))
        return parser.text()
    if suffix == ".pdf":
        return _read_pdf(path)
    raise ValueError(f"unsupported document type: {suffix}")


def _read_pdf(path: Path) -> str:
    try:
        import fitz  # type: ignore[import-not-found]  # PyMuPDF, optional
    except ImportError as exc:  # pragma: no cover - exercised only with the optional dep
        raise RuntimeError(
            "PDF ingestion requires PyMuPDF. Install with: pip install '.[ingest]'"
        ) from exc
    with fitz.open(path) as pdf:  # pragma: no cover - needs a real PDF + the optional dep
        return "\n".join(page.get_text("text") for page in pdf)


def chunk_text(
    text: str, *, jurisdiction_id: str, doc: SourceDoc
) -> list[Chunk]:
    """Split raw document text into clause-level chunks keyed by section number."""
    chunks: list[Chunk] = []
    chapter = ""
    section: str | None = None
    heading = ""
    body: list[str] = []

    def flush() -> None:
        if section is None:
            return
        prose = re.sub(r"\s+", " ", " ".join(body)).strip()
        full = f"{heading}. {prose}".strip() if heading else prose
        chunks.append(
            Chunk(
                id=f"{doc.doc_id}:{section}",
                jurisdiction_id=jurisdiction_id,
                doc_id=doc.doc_id,
                doc_short_code=doc.short_code,
                chapter=chapter,
                section=section,
                heading=heading,
                text=full,
            )
        )

    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if _CHAPTER_RE.match(line):
            flush()
            section, body, heading = None, [], ""
            chapter = re.sub(r"^\s*#{1,6}\s*", "", line).strip()
            continue
        m = _SECTION_RE.match(line)
        if m:
            flush()
            section = m.group("section")
            heading = m.group("title").strip()
            body = []
            continue
        if line.lstrip().startswith(">"):  # markdown blockquote (disclaimers) — skip
            continue
        body.append(line.strip())

    flush()
    return chunks


def ingest_document(jurisdiction_id: str, doc: SourceDoc, *, text: str | None = None) -> list[Chunk]:
    """Read (or accept inline ``text`` for re-ingest) and chunk a single document."""
    raw = text if text is not None else _read_document(doc)
    return chunk_text(raw, jurisdiction_id=jurisdiction_id, doc=doc)
