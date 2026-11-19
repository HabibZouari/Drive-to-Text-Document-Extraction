"""OCR languages offered to the user. Codes are Tesseract language codes."""

from app.extraction.errors import ExtractionError

SUPPORTED_LANGUAGES: dict[str, str] = {
    "eng": "English",
    "fra": "French",
    "ara": "Arabic",
}
DEFAULT_LANGUAGE = "eng"


def normalize_language(value: str | None) -> str:
    """Validate a language selection and return it in Tesseract's format.

    Accepts one code ("fra") or several joined with "+" ("fra+eng") for documents
    that mix languages. An empty value falls back to the default language.
    """
    if not value or not value.strip():
        return DEFAULT_LANGUAGE

    codes = [code.strip().lower() for code in value.split("+")]
    unknown = [code for code in codes if code not in SUPPORTED_LANGUAGES]
    if unknown:
        allowed = ", ".join(SUPPORTED_LANGUAGES)
        raise ExtractionError(
            f"Unsupported OCR language: {', '.join(unknown)}. Choose from: {allowed}."
        )
    return "+".join(dict.fromkeys(codes))  # drop duplicates, keep order
