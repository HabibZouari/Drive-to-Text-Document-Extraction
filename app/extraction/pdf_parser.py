"""Text extraction for native PDFs (the ones that carry a text layer), using pypdf."""

from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from app.extraction.errors import ExtractionError


def extract_pdf_text(path: Path) -> str:
    """Return the text layer of a PDF, non-empty pages separated by a blank line.

    Empty pages (blank or image-only) are skipped, and a page pypdf cannot read
    does not discard the pages that were readable. An empty string means the PDF
    has no text layer at all, which callers may treat as "scanned".
    """
    try:
        reader = PdfReader(path)
        if reader.is_encrypted and not reader.decrypt(""):
            raise ExtractionError("This PDF is password-protected.")
        page_count = len(reader.pages)
    except ExtractionError:
        raise
    except (PyPdfError, OSError, ValueError) as exc:
        raise ExtractionError("This file is not a valid PDF or is corrupted.") from exc

    texts: list[str] = []
    unreadable = 0
    for index in range(page_count):
        try:
            text = reader.pages[index].extract_text()
        except Exception:  # noqa: BLE001 - pypdf raises many types on malformed pages
            unreadable += 1
            continue
        if text.strip():
            texts.append(text.strip())

    if page_count and unreadable == page_count:
        raise ExtractionError("The text of this PDF could not be read.")
    return "\n\n".join(texts)
