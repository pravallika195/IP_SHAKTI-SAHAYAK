"""Secure Document Upload and Extraction Engine for IP-SAKTI Sahayak.

Processes applicant-uploaded innovation documents (PDF, DOCX, TXT) in an isolated sandbox.
CRITICAL CONSTRAINTS:
1. Uploaded applicant documents are PRIVATE to the submission and NEVER added to shared ChromaDB collections.
2. Validates file extension, magic byte signatures, and file size (< 15 MB).
3. Mitigates path traversal using werkzeug.utils.secure_filename and UUID prefixes.
4. Preserves document provenance, page counts, per-page text, and extraction warnings.
"""
from __future__ import annotations
import logging
import os
import re
import uuid
import zipfile
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF
from docx import Document as DocxDocument
from werkzeug.utils import secure_filename

from config import BASE_DIR
from data_loader import (
    PATENT_NUMBER_RE,
    _page_text,
    detect_language,
    infer_document_type
)

logger = logging.getLogger(__name__)

# Dedicated upload directory outside of data/documents knowledge base
UPLOAD_DIR = BASE_DIR / "uploads" / "applicant_documents"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}


def is_safe_path(base_dir: Path, target_path: Path) -> bool:
    """Ensure resolved target path stays within base directory to prevent traversal attacks."""
    try:
        base_dir_resolved = base_dir.resolve()
        target_path_resolved = target_path.resolve()
        return base_dir_resolved in target_path_resolved.parents or target_path_resolved == base_dir_resolved
    except Exception:
        return False


def validate_file_magic(content_header: bytes, ext: str) -> tuple[bool, str]:
    """Validate file content against magic byte signatures to prevent extension spoofing."""
    if ext == ".pdf":
        if b"%PDF-" not in content_header[:1024]:
            return False, "File header does not match valid PDF format (%PDF- missing)."
    elif ext == ".docx":
        if not content_header.startswith(b"PK\x03\x04"):
            return False, "File header does not match valid DOCX archive (PK signature missing)."
    elif ext == ".txt":
        # Check for binary null bytes that signify non-text executables
        if b"\x00" in content_header[:512]:
            return False, "Plain text file appears to contain binary or executable data."

    return True, ""


class DocumentExtractor:
    """Manages document validation, sandbox persistence, and multi-format extraction."""

    def __init__(self, upload_dir: Path = UPLOAD_DIR, max_size_bytes: int = MAX_FILE_SIZE_BYTES):
        self.upload_dir = upload_dir
        self.max_size_bytes = max_size_bytes
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_uploaded_file(self, file_storage, original_filename: str) -> tuple[Path, str, str]:
        """Saves an uploaded file with a cryptographically unique prefix to prevent overwriting and traversal."""
        safe_base = secure_filename(original_filename)
        if not safe_base:
            safe_base = "uploaded_document"

        ext = Path(safe_base).suffix.lower()
        if not ext and Path(original_filename).suffix:
            ext = Path(original_filename).suffix.lower()

        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported file extension '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}")

        doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        stored_filename = f"{doc_id}_{safe_base}"
        target_path = self.upload_dir / stored_filename

        if not is_safe_path(self.upload_dir, target_path):
            raise ValueError("Invalid target storage path (path traversal detected).")

        file_storage.seek(0)
        file_storage.save(target_path)

        file_size = target_path.stat().st_size
        if file_size > self.max_size_bytes:
            target_path.unlink(missing_ok=True)
            raise ValueError(f"File size ({file_size / (1024 * 1024):.2f} MB) exceeds maximum allowed limit (15 MB).")

        if file_size == 0:
            target_path.unlink(missing_ok=True)
            raise ValueError("Uploaded file is empty (0 bytes).")

        # Magic byte signature validation
        with open(target_path, "rb") as f:
            header_sample = f.read(1024)

        is_valid, reason = validate_file_magic(header_sample, ext)
        if not is_valid:
            target_path.unlink(missing_ok=True)
            raise ValueError(f"File signature validation failed: {reason}")

        return target_path, doc_id, stored_filename

    def extract(self, file_path: Path, original_filename: str, doc_id: str | None = None) -> dict[str, Any]:
        """Extracts text, metadata, page breakdown, and warnings from a validated document."""
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        ext = file_path.suffix.lower()
        doc_id = doc_id or f"doc_{uuid.uuid4().hex[:12]}"
        file_size = file_path.stat().st_size

        warnings: list[str] = []
        pages: list[dict[str, Any]] = []
        full_text = ""
        page_count = 0

        try:
            if ext == ".pdf":
                pages, full_text, page_count, pdf_warnings = self._extract_pdf(file_path, original_filename)
                warnings.extend(pdf_warnings)

            elif ext == ".docx":
                full_text, docx_warnings = self._extract_docx(file_path)
                page_count = 1  # Standard DOCX has no strict page concept without layout engine
                pages = [{"page_number": 1, "text": full_text, "char_count": len(full_text)}]
                warnings.extend(docx_warnings)

            elif ext == ".txt":
                full_text, txt_warnings = self._extract_txt(file_path)
                page_count = 1
                pages = [{"page_number": 1, "text": full_text, "char_count": len(full_text)}]
                warnings.extend(txt_warnings)

            else:
                raise ValueError(f"Unsupported file type: {ext}")

            # General extraction quality checks
            clean_text = full_text.strip()
            if not clean_text:
                status = "warning"
                warnings.append("Document extracted with zero readable characters. File may be image-only or corrupt.")
            elif len(clean_text) < 50:
                status = "warning"
                warnings.append("Document contains very little extractable text (< 50 characters).")
            else:
                status = "success"

            # Detect patent numbers and metadata
            patent_matches = list(set(PATENT_NUMBER_RE.findall(clean_text)))
            detected_lang = detect_language(clean_text)
            inferred_type = infer_document_type(file_path, clean_text)

            return {
                "status": status,
                "document_id": doc_id,
                "filename": original_filename,
                "stored_filename": file_path.name,
                "file_size": file_size,
                "file_type": ext.lstrip("."),
                "page_count": page_count,
                "text_length": len(clean_text),
                "extracted_text": clean_text,
                "pages": pages,
                "metadata": {
                    "language": detected_lang,
                    "document_type": inferred_type,
                    "detected_patent_numbers": patent_matches
                },
                "warnings": warnings,
                "error": None
            }

        except Exception as exc:
            logger.exception("Extraction failed for %s", original_filename)
            return {
                "status": "error",
                "document_id": doc_id,
                "filename": original_filename,
                "stored_filename": file_path.name,
                "file_size": file_size,
                "file_type": ext.lstrip("."),
                "page_count": 0,
                "text_length": 0,
                "extracted_text": "",
                "pages": [],
                "metadata": {},
                "warnings": warnings,
                "error": f"Document extraction failed: {str(exc)}"
            }

    def _extract_pdf(self, file_path: Path, source_name: str) -> tuple[list[dict], str, int, list[str]]:
        pages = []
        warnings = []
        full_text_parts = []

        try:
            with fitz.open(file_path) as pdf:
                page_count = len(pdf)
                if page_count == 0:
                    warnings.append("PDF contains 0 pages.")
                    return [], "", 0, warnings

                for page_idx in range(page_count):
                    page = pdf[page_idx]
                    page_text = _page_text(page, source_name)
                    clean_page = page_text.strip()
                    pages.append({
                        "page_number": page_idx + 1,
                        "text": clean_page,
                        "char_count": len(clean_page)
                    })
                    if clean_page:
                        full_text_parts.append(clean_page)

        except Exception as exc:
            raise ValueError(f"Corrupt or unreadable PDF: {str(exc)}") from exc

        full_text = "\n\n".join(full_text_parts)
        if not full_text:
            warnings.append("No digital text layer found across PDF pages (may require OCR scanning).")

        return pages, full_text, page_count, warnings

    def _extract_docx(self, file_path: Path) -> tuple[str, list[str]]:
        warnings = []
        paragraphs = []

        try:
            doc = DocxDocument(file_path)
            for p in doc.paragraphs:
                p_text = p.text.strip()
                if p_text:
                    paragraphs.append(p_text)

            # Extract tables
            for table_idx, table in enumerate(doc.tables, 1):
                table_lines = []
                for row in table.rows:
                    row_vals = [cell.text.strip() for cell in row.cells]
                    if any(row_vals):
                        table_lines.append(" | ".join(row_vals))
                if table_lines:
                    paragraphs.append(f"\n[Table {table_idx}]\n" + "\n".join(table_lines))

        except zipfile.BadZipFile:
            raise ValueError("Corrupt DOCX file (invalid zip archive structure).")
        except Exception as exc:
            raise ValueError(f"Could not read DOCX document: {str(exc)}") from exc

        full_text = "\n\n".join(paragraphs)
        if not full_text:
            warnings.append("DOCX document contains no readable text paragraphs or tables.")

        return full_text, warnings

    def _extract_txt(self, file_path: Path) -> tuple[str, list[str]]:
        warnings = []
        raw_bytes = file_path.read_bytes()

        # Try multiple decodings
        text = None
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if text is None:
            text = raw_bytes.decode("utf-8", errors="replace")
            warnings.append("Character decoding required replacement characters due to non-standard encoding.")

        return text.strip(), warnings


# Singleton instance
_extractor_instance = DocumentExtractor()

def get_document_extractor() -> DocumentExtractor:
    return _extractor_instance

