"""OCR for scanned PDFs: render each page to an image with PDFium, then run Tesseract."""

from pathlib import Path

import pypdfium2 as pdfium

from app.extraction.errors import ExtractionError
from app.extraction.ocr import recognize

RENDER_DPI = 200
MAX_OCR_PAGES = 20  # OCR is CPU-heavy: refuse very long scans instead of hanging the server


def extract_scanned_pdf_text(
    path: Path, language: str = "eng", max_pages: int = MAX_OCR_PAGES
) -> str:
    """OCR every page of a PDF that has no usable text layer."""
    try:
        document = pdfium.PdfDocument(path)
    except (pdfium.PdfiumError, OSError, ValueError) as exc:
        raise ExtractionError("This file is not a valid PDF or is corrupted.") from exc

    try:
        page_count = len(document)
        if page_count > max_pages:
            raise ExtractionError(
                f"This scanned PDF has {page_count} pages; OCR is limited to {max_pages} pages."
            )

        texts: list[str] = []
        for index in range(page_count):
            text = recognize(_render_page(document, index), language)
            if text:
                texts.append(text)
        return "\n\n".join(texts)
    finally:
        document.close()


def _render_page(document: pdfium.PdfDocument, index: int):
    page = document[index]
    try:
        return page.render(scale=RENDER_DPI / 72).to_pil()
    except pdfium.PdfiumError as exc:
        raise ExtractionError(f"Page {index + 1} of this PDF could not be rendered.") from exc
    finally:
        page.close()
