import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_drive_client
from app.drive.client import DriveFile
from app.drive.errors import (
    DriveConfigError,
    DriveUnavailableError,
    FolderNotAccessibleError,
)
from app.main import app

FOLDER_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"
FOLDER_URL = f"https://drive.google.com/drive/folders/{FOLDER_ID}?usp=sharing"


class FakeDrive:
    def __init__(self, files=None, error=None):
        self._files = files or []
        self._error = error
        self.requested_folder = None

    def list_files(self, folder_id):
        self.requested_folder = folder_id
        if self._error:
            raise self._error
        return self._files


@pytest.fixture
def client():
    yield TestClient(app)
    app.dependency_overrides.clear()


def use_drive(fake):
    app.dependency_overrides[get_drive_client] = lambda: fake


def test_lists_files_with_name_type_and_size(client):
    fake = FakeDrive(
        [
            DriveFile("1", "report.pdf", "application/pdf", 2048),
            DriveFile("2", "scan.jpg", "image/jpeg", None),
        ]
    )
    use_drive(fake)

    response = client.post("/api/folders", json={"url": FOLDER_URL})

    assert response.status_code == 200
    body = response.json()
    assert body["folder_id"] == FOLDER_ID
    assert body["files"] == [
        {
            "id": "1",
            "name": "report.pdf",
            "mime_type": "application/pdf",
            "type": "pdf",
            "size": 2048,
        },
        {"id": "2", "name": "scan.jpg", "mime_type": "image/jpeg", "type": "image", "size": None},
    ]
    assert fake.requested_folder == FOLDER_ID


def test_empty_folder_returns_an_empty_list(client):
    use_drive(FakeDrive([]))
    response = client.post("/api/folders", json={"url": FOLDER_URL})
    assert response.status_code == 200
    assert response.json()["files"] == []


def test_invalid_link_returns_400_with_message(client):
    use_drive(FakeDrive())
    response = client.post("/api/folders", json={"url": "https://example.com/nope"})
    assert response.status_code == 400
    assert "Google Drive" in response.json()["detail"]


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (FolderNotAccessibleError("private"), 404),
        (DriveConfigError("bad key"), 500),
        (DriveUnavailableError("down"), 502),
    ],
)
def test_drive_errors_map_to_http_status(client, error, status):
    use_drive(FakeDrive(error=error))
    response = client.post("/api/folders", json={"url": FOLDER_URL})
    assert response.status_code == status
    assert response.json()["detail"] == str(error)
