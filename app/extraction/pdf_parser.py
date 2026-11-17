"""Text extraction for native PDFs (the ones that carry a text layer), using pypdf."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.extraction.errors import ExtractionError


def extract_pdf_text(path: Path) -> str:
    """Return the text layer of a PDF, pages separated by a blank line."""
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("This PDF is password-protected.")
        pages = [page.extract_text() for page in reader.pages]
    except ExtractionError:
        raise
    except (PyPdfError, OSError, ValueError) as exc:
        raise ExtractionError("This file is not a valid PDF or is corrupted.") from exc

    return "\n\n".join(pages)
