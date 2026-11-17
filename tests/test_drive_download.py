import httpx
import pytest

from app.drive.client import DriveClient, DriveFile
from app.drive.errors import (
    DriveUnavailableError,
    FileTooLargeError,
    FolderNotAccessibleError,
)

MB = 1024 * 1024


def make_client(handler):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return DriveClient("test-key", http=http)


def test_download_writes_the_file_content(tmp_path):
    client = make_client(lambda request: httpx.Response(200, content=b"%PDF-1.4 data"))
    target = tmp_path / "file.pdf"

    client.download_file("file-id", target, max_bytes=MB)

    assert target.read_bytes() == b"%PDF-1.4 data"


def test_download_uses_the_media_endpoint_with_the_key():
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, content=b"x")

    file = DriveFile("abc", "a.pdf", "application/pdf", 1)
    with make_client(handler).temporary_download(file, MB):
        pass

    assert seen["path"].endswith("/files/abc")
    assert seen["params"] == {"alt": "media", "key": "test-key"}


def test_temporary_download_is_removed_after_use():
    client = make_client(lambda request: httpx.Response(200, content=b"png-bytes"))
    file = DriveFile("img1", "../../evil.png", "image/png", 9)

    with client.temporary_download(file, MB) as path:
        assert path.name == "img1.png"  # built from the id, never from the Drive name
        assert path.read_bytes() == b"png-bytes"

    assert not path.exists()
    assert not path.parent.exists()


def test_download_rejects_declared_size_above_limit(tmp_path):
    client = make_client(
        lambda request: httpx.Response(200, content=b"x", headers={"content-length": str(5 * MB)})
    )
    target = tmp_path / "big.pdf"

    with pytest.raises(FileTooLargeError, match="1 MB"):
        client.download_file("id", target, max_bytes=MB)
    assert not target.exists()


def test_download_stops_and_cleans_up_when_stream_exceeds_limit(tmp_path):
    client = make_client(lambda request: httpx.Response(200, content=b"a" * (2 * MB)))
    target = tmp_path / "streamed.pdf"

    with pytest.raises(FileTooLargeError):
        client.download_file("id", target, max_bytes=MB)
    assert not target.exists()


@pytest.mark.parametrize("status", [403, 404])
def test_inaccessible_file_gets_a_file_specific_message(tmp_path, status):
    body = {"error": {"code": status, "errors": [{"reason": "notFound"}]}}
    client = make_client(lambda request: httpx.Response(status, json=body))

    with pytest.raises(FolderNotAccessibleError, match="cannot be downloaded"):
        client.download_file("id", tmp_path / "x.pdf", max_bytes=MB)


def test_network_failure_during_download_is_reported_as_unavailable(tmp_path):
    def handler(request):
        raise httpx.ReadTimeout("slow")

    with pytest.raises(DriveUnavailableError, match="Could not download"):
        make_client(handler).download_file("id", tmp_path / "x.pdf", max_bytes=MB)
