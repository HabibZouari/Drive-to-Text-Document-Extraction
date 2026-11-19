from pathlib import Path

import pytest

from app.extraction.errors import ExtractionError
from app.extraction.models import Method
from app.extraction.router import extract_text

PATH = Path("irrelevant")


PDF_TEXT = "text layer long enough to be a real document"


def fake_pdf(path):
    return PDF_TEXT


def fake_scanned_pdf(path, language):
    return f"ocr of scanned pdf ({language})"


def fake_image(path, language):
    return f"text from image ({language})"


def route(kind, language="eng", **overrides):
    extractors = {
        "pdf_extractor": fake_pdf,
        "scanned_pdf_extractor": fake_scanned_pdf,
        "image_extractor": fake_image,
        **overrides,
    }
    return extract_text(PATH, kind, language, **extractors)


def test_pdf_goes_to_the_pdf_parser():
    result = route("pdf")
    assert result.text == PDF_TEXT
    assert result.method is Method.PDF_PARSER


def test_image_goes_to_ocr():
    result = route("image")
    assert result.text == "text from image (eng)"
    assert result.method is Method.OCR


def test_ocr_receives_the_requested_language():
    assert route("image", language="fra").text == "text from image (fra)"


def test_pdf_never_calls_the_ocr_engine():
    def must_not_run(path, language):
        raise AssertionError("OCR must not run for a native PDF")

    assert route("pdf", image_extractor=must_not_run).method is Method.PDF_PARSER


def test_image_never_calls_the_pdf_parser():
    def must_not_run(path):
        raise AssertionError("PDF parser must not run for an image")

    assert route("image", pdf_extractor=must_not_run).method is Method.OCR


@pytest.mark.parametrize("kind", ["docx", "txt", ""])
def test_unsupported_kind_is_rejected(kind):
    with pytest.raises(ExtractionError, match="Unsupported file type"):
        route(kind)


def test_extractor_errors_propagate_to_the_caller():
    def failing(path):
        raise ExtractionError("boom")

    with pytest.raises(ExtractionError, match="boom"):
        route("pdf", pdf_extractor=failing)


def test_method_values_are_the_strings_used_in_the_json_export():
    assert Method.PDF_PARSER.value == "pdf_parser"
    assert Method.OCR.value == "ocr"
