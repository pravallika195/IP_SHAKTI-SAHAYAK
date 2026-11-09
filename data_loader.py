"""Load PDF, DOCX and TXT knowledge sources with page/source metadata.

Scanned PDFs: set ENABLE_OCR=true and install Tesseract plus eng/hin/tel language packs.
"""
from __future__ import annotations
import os
import logging
import re
import unicodedata
from pathlib import Path
import fitz
from docx import Document as DocxDocument
from langdetect import detect, DetectorFactory
from config import DATA_DIR, ENABLE_OCR, OCR_LANGUAGES

TESSERACT_DIR = Path(r"C:\Program Files\Tesseract-OCR")
TESSERACT_EXE = TESSERACT_DIR / "tesseract.exe"

if TESSERACT_EXE.exists():
    os.environ["PATH"] = (
        str(TESSERACT_DIR) + os.pathsep + os.environ.get("PATH", "")
    )

logger = logging.getLogger(__name__) 
DetectorFactory.seed = 0
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
PATENT_NUMBER_RE = re.compile(r"\b(?:IN|WO|US|EP|CN|JP|KR)\s?\d{4,}[A-Z0-9/.-]*\b", re.I)


def detect_language(text: str) -> str:
    sample = unicodedata.normalize("NFKC", (text or "")).strip()[:4000]
    if len(sample) < 30:
        return "und"
    try:
        lang = detect(sample)
        return lang if lang in {"en", "hi", "te", "ta", "ml"} else lang
    except Exception:
        return "und"


def infer_document_type(path: Path, text: str) -> str:
    # Prioritize explicit folder structure
    path_str = str(path).lower()
    if "traditional_knowledge" in path_str:
        return "traditional_knowledge"
    if "research_papers" in path_str:
        return "research_paper"
    if "patents" in path_str:
        return "patent"

    # Fallback heuristics based on filename and header text
    label = (path.name + " " + text[:1500]).lower()
    if any(x in label for x in ("traditional knowledge", "tkdl", "ayurveda", "formulation", "herbal", "monograph")):
        return "traditional_knowledge"
    if any(x in label for x in ("claims", "what is claimed", "patent", "publication number", "application no")):
        return "patent"
    if any(x in label for x in ("research", "journal", "doi", "abstract")):
        return "research_paper"
    return "other"


def _page_text(page: fitz.Page, source: str) -> str:
    text = page.get_text("text").strip()

    if not ENABLE_OCR:
        return text

    # Estimate how much of the page is occupied by images.
    image_coverage = 0.0

    try:
        page_area = page.rect.get_area()

        if page_area > 0:
            image_area = sum(
                fitz.Rect(info["bbox"]).intersect(page.rect).get_area()
                for info in page.get_image_info()
            )

            image_coverage = min(1.0, image_area / page_area)

    except Exception as exc:
        logger.warning(
            "Could not inspect images in %s page %s: %s",
            source, page.number + 1, exc
        )

    # OCR truly empty pages and scanned pages where digital text is absent or negligible.
    needs_ocr = (
        not text
        or (len(text) < 50 and image_coverage >= 0.50)
    )

    if not needs_ocr:
        return text

    try:
        text_page = page.get_textpage_ocr(
            language=OCR_LANGUAGES,
            dpi=300,
            full=True
        )

        ocr_text = page.get_text(
            "text",
            textpage=text_page
        ).strip()

        if ocr_text:
            logger.info(
                "OCR completed: %s, page %s, coverage %.2f",
                source,
                page.number + 1,
                image_coverage
            )
            return ocr_text

        return text

    except Exception as exc:
        logger.exception(
            "OCR failed for %s page %s: %s",
            source, page.number + 1, exc
        )
        return text


def _base_metadata(path: Path, text: str, page: int, document_text: str | None = None) -> dict:
    full_text = document_text or text
    patent_match = PATENT_NUMBER_RE.search(full_text)
    priority_match = re.search(r"(?:priority date|date of priority)\s*[:：]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", full_text, re.I)
    publication_date_match = re.search(r"(?:publication date|date of publication)\s*[:：]?\s*([0-9]{1,2}[./-][0-9]{1,2}[./-][0-9]{2,4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", full_text, re.I)
    return {
        "source": path.name,
        "source_path": str(path.relative_to(DATA_DIR)) if path.is_relative_to(DATA_DIR) else path.name,
        "page": int(page),
        "document_type": infer_document_type(path, full_text),
        "language": detect_language(text),
        "publication_number": patent_match.group(0).replace(" ", "") if patent_match else "",
        "priority_date": priority_match.group(1) if priority_match else "",
        "publication_date": publication_date_match.group(1) if publication_date_match else "",
    }


def load_documents(data_dir: str | Path = DATA_DIR, max_files: int | None = None) -> list[dict]:
    root = Path(data_dir)
    if not root.exists():
        raise FileNotFoundError(f"Document directory does not exist: {root}")
    files = sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)
    if max_files is not None and max_files > 0:
        files = files[:max_files]
    documents: list[dict] = []
    for path in files:
        try:
            suffix = path.suffix.lower()
            if suffix == ".pdf":
                with fitz.open(path) as pdf:
                    page_texts = [_page_text(page, path.name) for page in pdf]
                full_text = "\n".join(page_texts)
                for page_index, text in enumerate(page_texts):
                    if text:
                        documents.append({"text": text, **_base_metadata(path, text, page_index + 1, full_text)})
            elif suffix == ".docx":
                doc = DocxDocument(path)
                text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
                # Include table content, common in patent and technical documents.
                for table in doc.tables:
                    for row in table.rows:
                        text += "\n" + " | ".join(cell.text.strip() for cell in row.cells)
                if text.strip():
                    documents.append({"text": text, **_base_metadata(path, text, 0, text)})
            else:
                text = path.read_text(encoding="utf-8", errors="replace").strip()
                if text:
                    documents.append({"text": text, **_base_metadata(path, text, 0, text)})
            logger.info("Loaded %s", path)
        except Exception:
            logger.exception("Failed to load %s", path)
    logger.info("Loaded %d text units from %d files", len(documents), len(files))
    return documents


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for item in load_documents():
        print(item["source"], item["page"], item["language"], item["document_type"], item["text"][:160])
