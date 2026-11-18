"""Choose the extraction pipeline for a file: PDF parser for PDFs, OCR for images."""

from collections.abc import Callable
from pathlib import Path

from app.extraction.errors import ExtractionError
from app.extraction.models import ExtractionResult, Method
from app.extraction.ocr import extract_image_text
from app.extraction.pdf_parser import extract_pdf_text


def extract_text(
    path: Path,
    kind: str,
    language: str = "eng",
    *,
    pdf_extractor: Callable[[Path], str] = extract_pdf_text,
    image_extractor: Callable[[Path, str], str] = extract_image_text,
) -> ExtractionResult:
    """Extract the text of the file at ``path``.

    ``kind`` is the processing family reported by the Drive layer ("pdf" or "image").
    The extractors are injectable so the routing can be tested without real files.
    """
    if kind == "pdf":
        return ExtractionResult(text=pdf_extractor(path), method=Method.PDF_PARSER)
    if kind == "image":
        return ExtractionResult(text=image_extractor(path, language), method=Method.OCR)
    raise ExtractionError(f"Unsupported file type: {kind}.")
