"""Choose the extraction pipeline for a file: PDF parser for PDFs, OCR for images."""

from collections.abc import Callable
from pathlib import Path

from app.extraction.errors import ExtractionError
from app.extraction.languages import normalize_language
from app.extraction.models import ExtractionResult, Method
from app.extraction.ocr import extract_image_text
from app.extraction.pdf_ocr import extract_scanned_pdf_text
from app.extraction.pdf_parser import extract_pdf_text

# A PDF whose text layer holds fewer characters than this is treated as a scan.
SCANNED_MIN_CHARS = 20


def extract_text(
    path: Path,
    kind: str,
    language: str = "eng",
    *,
    pdf_extractor: Callable[[Path], str] = extract_pdf_text,
    scanned_pdf_extractor: Callable[[Path, str], str] = extract_scanned_pdf_text,
    image_extractor: Callable[[Path, str], str] = extract_image_text,
) -> ExtractionResult:
    """Extract the text of the file at ``path``.

    ``kind`` is the processing family reported by the Drive layer ("pdf" or "image").
    A PDF is read with the PDF parser first; if it has no usable text layer it is
    treated as a scan and sent to OCR. The extractors are injectable so the routing
    can be tested without real files.
    """
    language = normalize_language(language)
    if kind == "pdf":
        text = pdf_extractor(path)
        if len(text.strip()) >= SCANNED_MIN_CHARS:
            return ExtractionResult(text=text, method=Method.PDF_PARSER)
        return ExtractionResult(text=scanned_pdf_extractor(path, language), method=Method.OCR)
    if kind == "image":
        return ExtractionResult(text=image_extractor(path, language), method=Method.OCR)
    raise ExtractionError(f"Unsupported file type: {kind}.")
