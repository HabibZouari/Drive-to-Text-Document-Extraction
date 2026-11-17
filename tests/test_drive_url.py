import pytest

from app.drive.errors import InvalidDriveUrlError
from app.drive.url import extract_folder_id

FOLDER_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"


@pytest.mark.parametrize(
    "url",
    [
        f"https://drive.google.com/drive/folders/{FOLDER_ID}",
        f"https://drive.google.com/drive/folders/{FOLDER_ID}?usp=sharing",
        f"https://drive.google.com/drive/folders/{FOLDER_ID}/",
        f"https://drive.google.com/drive/u/0/folders/{FOLDER_ID}",
        f"https://drive.google.com/open?id={FOLDER_ID}",
        f"https://drive.google.com/folderview?id={FOLDER_ID}",
        f"  https://drive.google.com/drive/folders/{FOLDER_ID}  ",
    ],
)
def test_extracts_folder_id_from_supported_links(url):
    assert extract_folder_id(url) == FOLDER_ID


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "not a link",
        "https://example.com/drive/folders/" + FOLDER_ID,
        "https://drive.google.com/drive/my-drive",
        "https://drive.google.com/drive/folders/short",
        "ftp://drive.google.com/drive/folders/" + FOLDER_ID,
    ],
)
def test_rejects_links_that_are_not_drive_folders(url):
    with pytest.raises(InvalidDriveUrlError):
        extract_folder_id(url)


def test_single_file_link_gets_a_specific_message():
    url = f"https://drive.google.com/file/d/{FOLDER_ID}/view"
    with pytest.raises(InvalidDriveUrlError, match="single file"):
        extract_folder_id(url)
