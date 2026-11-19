import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.extraction.errors import ExtractionError
from app.extraction.languages import DEFAULT_LANGUAGE, normalize_language
from app.extraction.ocr import recognize
from app.extraction.router import extract_text
from app.main import app


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("eng", "eng"),
        ("fra", "fra"),
        ("ara", "ara"),
        ("FRA", "fra"),
        (" fra + eng ", "fra+eng"),
        ("fra+fra+eng", "fra+eng"),
        ("", DEFAULT_LANGUAGE),
        ("   ", DEFAULT_LANGUAGE),
        (None, DEFAULT_LANGUAGE),
    ],
)
def test_normalize_language_accepts_supported_values(value, expected):
    assert normalize_language(value) == expected


@pytest.mark.parametrize("value", ["deu", "fra+deu", "english", "fra,eng"])
def test_normalize_language_rejects_unsupported_values(value):
    with pytest.raises(ExtractionError, match="Unsupported OCR language"):
        normalize_language(value)


def test_router_validates_the_language_before_extracting():
    def must_not_run(*args):
        raise AssertionError("extraction must not start with an invalid language")

    with pytest.raises(ExtractionError, match="Unsupported OCR language"):
        extract_text(
            Path("x"),
            "image",
            "klingon",
            pdf_extractor=must_not_run,
            image_extractor=must_not_run,
        )


def test_router_normalises_the_language_given_to_ocr():
    seen = {}

    def fake_image(path, language):
        seen["language"] = language
        return "text"

    extract_text(Path("x"), "image", "FRA+eng", image_extractor=fake_image)
    assert seen["language"] == "fra+eng"


def test_languages_endpoint_lists_the_choices():
    response = TestClient(app).get("/api/languages")
    assert response.status_code == 200
    assert response.json() == [
        {"code": "eng", "label": "English"},
        {"code": "fra", "label": "French"},
        {"code": "ara", "label": "Arabic"},
    ]


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract is not installed")
def test_missing_language_pack_gets_a_specific_message():
    with pytest.raises(ExtractionError, match="language pack"):
        recognize(Image.new("RGB", (40, 40), "white"), language="zzz")
