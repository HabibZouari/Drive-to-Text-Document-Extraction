import shutil
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfWriter

from app.extraction import pdf_ocr
from app.extraction.errors import ExtractionError
from app.extraction.models import Method
from app.extraction.pdf_ocr import extract_scanned_pdf_text
from app.extraction.router import SCANNED_MIN_CHARS, extract_text

PATH = Path("irrelevant")


def never_called(*args):
    raise AssertionError("this extractor must not be called")


def route_pdf(text_layer, language="eng", scanned=None):
    return extract_text(
        PATH,
        "pdf",
        language,
        pdf_extractor=lambda path: text_layer,
        scanned_pdf_extractor=scanned or (lambda path, lang: f"scan read as {lang}"),
    )


# --- detection rule in the router -------------------------------------------------


@pytest.mark.parametrize("text_layer", ["", "   \n\t ", "x" * (SCANNED_MIN_CHARS - 1)])
def test_pdf_without_enough_text_is_sent_to_ocr(text_layer):
    result = route_pdf(text_layer)
    assert result.method is Method.OCR
    assert result.text == "scan read as eng"


def test_whitespace_padding_does_not_count_as_text():
    padded = "ab" + " \n" * 100
    assert route_pdf(padded).method is Method.OCR


def test_pdf_with_enough_text_stays_on_the_parser():
    text_layer = "x" * SCANNED_MIN_CHARS
    result = route_pdf(text_layer, scanned=never_called)
    assert result.method is Method.PDF_PARSER
    assert result.text == text_layer


def test_fallback_receives_the_selected_language():
    assert route_pdf("", language="ara").text == "scan read as ara"


def test_parser_error_does_not_trigger_the_fallback():
    def broken(path):
        raise ExtractionError("not a valid PDF")

    with pytest.raises(ExtractionError, match="not a valid PDF"):
        extract_text(PATH, "pdf", pdf_extractor=broken, scanned_pdf_extractor=never_called)


def test_ocr_error_on_a_scan_propagates():
    def failing(path, language):
        raise ExtractionError("ocr failed")

    with pytest.raises(ExtractionError, match="ocr failed"):
        route_pdf("", scanned=failing)


# --- page rendering and OCR ---------------------------------------------------------


def blank_pdf(tmp_path, pages):
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    path = tmp_path / "scan.pdf"
    with path.open("wb") as handle:
        writer.write(handle)
    return path


def test_every_page_is_rendered_and_read_in_order(monkeypatch, tmp_path):
    reads = iter(["first page", "second page", "third page"])
    monkeypatch.setattr(pdf_ocr, "recognize", lambda image, language: next(reads))

    assert extract_scanned_pdf_text(blank_pdf(tmp_path, 3)) == (
        "first page\n\nsecond page\n\nthird page"
    )


def test_pages_with_no_recognised_text_are_skipped(monkeypatch, tmp_path):
    reads = iter(["kept", "", "also kept"])
    monkeypatch.setattr(pdf_ocr, "recognize", lambda image, language: next(reads))

    assert extract_scanned_pdf_text(blank_pdf(tmp_path, 3)) == "kept\n\nalso kept"


def test_language_and_rendered_image_are_passed_to_ocr(monkeypatch, tmp_path):
    seen = {}

    def fake(image, language):
        seen.update(language=language, mode=image.mode, size=image.size)
        return "x"

    monkeypatch.setattr(pdf_ocr, "recognize", fake)
    extract_scanned_pdf_text(blank_pdf(tmp_path, 1), language="fra")

    assert seen["language"] == "fra"
    assert seen["mode"] in ("RGB", "RGBA")
    # a 200x200 pt page rendered at 200 dpi is about 556 px wide
    assert 500 < seen["size"][0] < 620


def test_scans_above_the_page_limit_are_refused_before_any_ocr(monkeypatch, tmp_path):
    monkeypatch.setattr(pdf_ocr, "recognize", never_called)
    with pytest.raises(ExtractionError, match="limited to 2 pages"):
        extract_scanned_pdf_text(blank_pdf(tmp_path, 3), max_pages=2)


def test_invalid_pdf_raises_a_clear_error(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_text("not a pdf")
    with pytest.raises(ExtractionError, match="not a valid PDF"):
        extract_scanned_pdf_text(path)


# --- real end-to-end run ---------------------------------------------------------------


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_scanned_pdf_goes_through_the_real_pipeline(tmp_path):
    page = Image.new("RGB", (1240, 400), "white")
    font = ImageFont.load_default(size=80)
    ImageDraw.Draw(page).text((60, 120), "SCANNED INVOICE 2026", font=font, fill="black")
    path = tmp_path / "scanned.pdf"
    page.save(path, "PDF", resolution=150)

    result = extract_text(path, "pdf", "eng")

    assert result.method is Method.OCR
    assert "SCANNED" in result.text
