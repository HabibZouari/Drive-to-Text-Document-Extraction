import shutil

import pytesseract
import pytest
from PIL import Image, ImageDraw, ImageFont

from app.extraction import ocr
from app.extraction.errors import ExtractionError
from app.extraction.ocr import extract_image_text


@pytest.fixture
def png(tmp_path):
    path = tmp_path / "image.png"
    Image.new("RGB", (50, 50), "white").save(path)
    return path


def patch_ocr(monkeypatch, result=None, error=None):
    calls = {}

    def fake(image, lang, timeout):
        calls.update(lang=lang, timeout=timeout, mode=image.mode)
        if error:
            raise error
        return result

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", fake)
    return calls


def test_returns_stripped_text_and_passes_language_and_timeout(monkeypatch, png):
    calls = patch_ocr(monkeypatch, result="  hello \n")

    assert extract_image_text(png, language="fra") == "hello"
    assert calls["lang"] == "fra"
    assert calls["timeout"] == ocr.OCR_TIMEOUT_SECONDS
    assert calls["mode"] == "RGB"


def test_not_an_image_raises_a_clear_error(tmp_path):
    path = tmp_path / "fake.png"
    path.write_text("definitely not an image")
    with pytest.raises(ExtractionError, match="not a valid image"):
        extract_image_text(path)


def test_missing_tesseract_binary_is_reported(monkeypatch, png):
    patch_ocr(monkeypatch, error=pytesseract.TesseractNotFoundError())
    with pytest.raises(ExtractionError, match="not installed"):
        extract_image_text(png)


def test_tesseract_failure_is_reported(monkeypatch, png):
    patch_ocr(monkeypatch, error=pytesseract.TesseractError(1, "bad language"))
    with pytest.raises(ExtractionError, match="failed to read"):
        extract_image_text(png)


def test_timeout_is_reported(monkeypatch, png):
    patch_ocr(monkeypatch, error=RuntimeError("Tesseract process timeout"))
    with pytest.raises(ExtractionError, match="took too long"):
        extract_image_text(png)


def test_transparent_png_is_flattened_onto_white(monkeypatch, tmp_path):
    path = tmp_path / "transparent.png"
    Image.new("RGBA", (10, 10), (0, 0, 0, 0)).save(path)
    seen = {}

    def fake(image, lang, timeout):
        seen["mode"] = image.mode
        seen["pixel"] = image.getpixel((0, 0))
        return ""

    monkeypatch.setattr(ocr.pytesseract, "image_to_string", fake)
    extract_image_text(path)

    assert seen == {"mode": "RGB", "pixel": (255, 255, 255)}


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_real_tesseract_reads_printed_text(tmp_path):
    image = Image.new("RGB", (700, 160), "white")
    font = ImageFont.load_default(size=72)
    ImageDraw.Draw(image).text((30, 30), "HELLO 2026", font=font, fill="black")
    path = tmp_path / "hello.png"
    image.save(path)

    assert "HELLO" in extract_image_text(path, language="eng")
