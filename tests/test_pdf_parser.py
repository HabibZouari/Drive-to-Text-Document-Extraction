import pytest
from pypdf import PdfWriter

from app.extraction import pdf_parser
from app.extraction.errors import ExtractionError
from app.extraction.pdf_parser import extract_pdf_text


class FakePage:
    def __init__(self, text=None, error=None):
        self._text = text
        self._error = error

    def extract_text(self):
        if self._error:
            raise self._error
        return self._text


class FakeReader:
    is_encrypted = False

    def __init__(self, pages):
        self.pages = pages


def use_pages(monkeypatch, pages):
    monkeypatch.setattr(pdf_parser, "PdfReader", lambda path: FakeReader(pages))


def test_pages_are_joined_with_a_blank_line(monkeypatch, tmp_path):
    use_pages(monkeypatch, [FakePage("first page"), FakePage("second page")])
    assert extract_pdf_text(tmp_path / "x.pdf") == "first page\n\nsecond page"


def test_empty_pages_are_skipped_without_leaving_gaps(monkeypatch, tmp_path):
    use_pages(monkeypatch, [FakePage("one"), FakePage(""), FakePage("  \n "), FakePage("two")])
    assert extract_pdf_text(tmp_path / "x.pdf") == "one\n\ntwo"


def test_unreadable_page_does_not_discard_readable_pages(monkeypatch, tmp_path):
    use_pages(monkeypatch, [FakePage("kept"), FakePage(error=KeyError("/Font")), FakePage("also")])
    assert extract_pdf_text(tmp_path / "x.pdf") == "kept\n\nalso"


def test_pdf_where_every_page_is_unreadable_is_an_error(monkeypatch, tmp_path):
    use_pages(monkeypatch, [FakePage(error=ValueError("bad")), FakePage(error=ValueError("bad"))])
    with pytest.raises(ExtractionError, match="could not be read"):
        extract_pdf_text(tmp_path / "x.pdf")


def test_pdf_made_only_of_blank_pages_returns_empty_text(tmp_path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    writer.add_blank_page(width=200, height=200)
    path = tmp_path / "blank.pdf"
    with path.open("wb") as handle:
        writer.write(handle)

    assert extract_pdf_text(path) == ""


def test_corrupted_file_raises_a_clear_error(tmp_path):
    path = tmp_path / "broken.pdf"
    path.write_text("this is not a pdf")
    with pytest.raises(ExtractionError, match="not a valid PDF"):
        extract_pdf_text(path)
