"""
Low-level file text extraction for PDF, DOCX, TXT, CSV.
Returns plain text plus (for PDF) page-level spans so agents can cite pages.
"""
from __future__ import annotations
import csv
import io
from dataclasses import dataclass, field


@dataclass
class ExtractedPage:
    page_number: int
    text: str


@dataclass
class ParsedDocument:
    full_text: str
    pages: list[ExtractedPage] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def parse_pdf(file_bytes: bytes) -> ParsedDocument:
    from pypdf import PdfReader

    warnings: list[str] = []
    pages: list[ExtractedPage] = []
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        for i, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            if not text.strip():
                warnings.append(f"Page {i} produced no extractable text (may be scanned/image-based).")
            pages.append(ExtractedPage(page_number=i, text=text))
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"PDF parsing error: {exc}")
    full_text = "\n\n".join(p.text for p in pages)
    return ParsedDocument(full_text=full_text, pages=pages, warnings=warnings)


def parse_docx(file_bytes: bytes) -> ParsedDocument:
    from docx import Document as DocxDocument

    warnings: list[str] = []
    try:
        doc = DocxDocument(io.BytesIO(file_bytes))
        paras = [p.text for p in doc.paragraphs if p.text.strip()]
        for table in doc.tables:
            for row in table.rows:
                paras.append(" | ".join(c.text for c in row.cells))
        full_text = "\n".join(paras)
        if not full_text.strip():
            warnings.append("DOCX produced no extractable text.")
    except Exception as exc:  # noqa: BLE001
        full_text = ""
        warnings.append(f"DOCX parsing error: {exc}")
    return ParsedDocument(full_text=full_text, pages=[ExtractedPage(1, full_text)], warnings=warnings)


def parse_txt(file_bytes: bytes) -> ParsedDocument:
    warnings: list[str] = []
    try:
        text = file_bytes.decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        text = ""
        warnings.append(f"TXT decode error: {exc}")
    return ParsedDocument(full_text=text, pages=[ExtractedPage(1, text)], warnings=warnings)


def parse_csv(file_bytes: bytes) -> ParsedDocument:
    warnings: list[str] = []
    try:
        text = file_bytes.decode("utf-8", errors="replace")
        reader = csv.reader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            warnings.append("CSV is empty.")
        rendered = "\n".join(" | ".join(row) for row in rows)
    except Exception as exc:  # noqa: BLE001
        rendered = ""
        warnings.append(f"CSV parsing error: {exc}")
    return ParsedDocument(full_text=rendered, pages=[ExtractedPage(1, rendered)], warnings=warnings)


def parse_file(filename: str, file_bytes: bytes) -> ParsedDocument:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "pdf":
        return parse_pdf(file_bytes)
    if ext == "docx":
        return parse_docx(file_bytes)
    if ext == "csv":
        return parse_csv(file_bytes)
    if ext in ("txt", "md"):
        return parse_txt(file_bytes)
    return ParsedDocument(full_text="", warnings=[f"Unsupported file extension: .{ext}"])
