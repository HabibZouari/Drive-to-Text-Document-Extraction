from dataclasses import dataclass
from enum import StrEnum


class Method(StrEnum):
    """How the text of a file was obtained."""

    PDF_PARSER = "pdf_parser"
    OCR = "ocr"


@dataclass(frozen=True)
class ExtractionResult:
    text: str
    method: Method
