"""Patent-aware chunking that preserves section, page and source metadata."""
from __future__ import annotations
import re
import logging
from config import CHUNK_SIZE, CHUNK_OVERLAP

logger = logging.getLogger(__name__)
SECTION_PATTERNS = [
    ("abstract", r"^\s*(abstract|सारांश|సారాంశం)\s*[:.]?\s*$"),
    ("technical_field", r"^\s*(field of (the )?invention|technical field)\s*[:.]?\s*$"),
    ("background", r"^\s*(background|prior art|पृष्ठभूमि|పూర్వ\s+కళ)\s*[:.]?\s*$"),
    ("summary", r"^\s*(summary|संक्षेप)\s*[:.]?\s*$"),
    ("claims", r"^\s*(what is claimed is|we claim|claims?)\s*[:.]?\s*$"),
    ("description", r"^\s*(detailed description|description|विवरण|వివరణ)\s*[:.]?\s*$"),
    ("examples", r"^\s*(examples?|experimental examples?)\s*[:.]?\s*$"),
    ("references", r"^\s*(references|bibliography)\s*[:.]?\s*$"),
]


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    text = re.sub(r"[ \t]+", " ", text).strip()
    if not text:
        return []
    units = [u.strip() for u in re.split(r"\n\s*\n|(?<=[.!?।])\s+", text) if u.strip()]
    chunks, current = [], ""
    for unit in units:
        if len(unit) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(unit):
                piece = unit[start:start + chunk_size].strip()
                if piece:
                    chunks.append(piece)
                start += max(1, chunk_size - overlap)
            continue
        candidate = f"{current} {unit}".strip() if current else unit
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            if current:
                chunks.append(current)
            tail = current[-overlap:] if overlap and current else ""
            current = f"{tail} {unit}".strip() if tail else unit
    if current:
        chunks.append(current)
    return chunks


def _section_segments(text: str) -> list[tuple[str, str]]:
    """Split a text unit at recognizable headings while retaining the heading text."""
    segments, current_section, buffer = [], "body", []
    compiled = [(section, re.compile(pattern, re.I)) for section, pattern in SECTION_PATTERNS]
    for line in text.splitlines():
        stripped = line.strip()
        matched = next((section for section, pattern in compiled if stripped and pattern.match(stripped)), None)
        if matched:
            if buffer:
                segments.append((current_section, "\n".join(buffer).strip()))
            current_section, buffer = matched, [line]
        else:
            buffer.append(line)
    if buffer:
        segments.append((current_section, "\n".join(buffer).strip()))
    return [(section, content) for section, content in segments if content]


def chunk_documents(documents: list[dict], chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("Require chunk_size > overlap >= 0")
    output = []
    for doc_index, doc in enumerate(documents):
        for section, section_text in _section_segments(doc.get("text", "")):
            for chunk_index, chunk in enumerate(_split_text(section_text, chunk_size, overlap)):
                metadata = {k: v for k, v in doc.items() if k != "text"}
                metadata["section"] = section
                metadata["chunk_index"] = int(chunk_index)
                chunk_id = f"{doc.get('source','doc')}_p{doc.get('page',0)}_{doc_index}_{section}_{chunk_index}"
                output.append({"text": chunk, "chunk_id": chunk_id, **metadata})
    logger.info("Created %d section-aware chunks from %d source units", len(output), len(documents))
    return output
