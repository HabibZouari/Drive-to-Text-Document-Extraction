import httpx
import pytest

from app.drive.client import DriveClient, DriveFile
from app.drive.errors import (
    DriveConfigError,
    DriveUnavailableError,
    FolderNotAccessibleError,
)

FOLDER_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"


def make_client(handler, api_key="test-key"):
    http = httpx.Client(transport=httpx.MockTransport(handler))
    return DriveClient(api_key, http=http)


def error_body(code, reason):
    return {"error": {"code": code, "errors": [{"reason": reason}]}}


def test_lists_supported_files_across_pages():
    pages = [
        {
            "files": [{"id": "a", "name": "a.pdf", "mimeType": "application/pdf", "size": "10"}],
            "nextPageToken": "next",
        },
        {"files": [{"id": "b", "name": "b.png", "mimeType": "image/png"}]},
    ]
    calls = []

    def handler(request):
        calls.append(dict(request.url.params))
        return httpx.Response(200, json=pages[len(calls) - 1])

    files = make_client(handler).list_files(FOLDER_ID)

    assert files == [
        DriveFile("a", "a.pdf", "application/pdf", 10),
        DriveFile("b", "b.png", "image/png", None),
    ]
    assert calls[1]["pageToken"] == "next"
    assert FOLDER_ID in calls[0]["q"]


def test_empty_folder_returns_empty_list():
    client = make_client(lambda request: httpx.Response(200, json={"files": []}))
    assert client.list_files(FOLDER_ID) == []


def test_missing_api_key_is_a_config_error():
    client = make_client(lambda request: httpx.Response(200, json={}), api_key="")
    with pytest.raises(DriveConfigError, match="GOOGLE_API_KEY"):
        client.list_files(FOLDER_ID)


@pytest.mark.parametrize("status", [403, 404])
def test_private_or_unknown_folder_is_reported_as_not_accessible(status):
    client = make_client(
        lambda request: httpx.Response(status, json=error_body(status, "notFound"))
    )
    with pytest.raises(FolderNotAccessibleError, match="Anyone with the link"):
        client.list_files(FOLDER_ID)


def test_invalid_api_key_is_a_config_error():
    client = make_client(lambda request: httpx.Response(400, json=error_body(400, "keyInvalid")))
    with pytest.raises(DriveConfigError, match="invalid"):
        client.list_files(FOLDER_ID)


def test_disabled_drive_api_is_a_config_error():
    client = make_client(
        lambda request: httpx.Response(403, json=error_body(403, "accessNotConfigured"))
    )
    with pytest.raises(DriveConfigError, match="not enabled"):
        client.list_files(FOLDER_ID)


def test_rate_limit_is_reported_as_unavailable_not_private():
    client = make_client(
        lambda request: httpx.Response(403, json=error_body(403, "rateLimitExceeded"))
    )
    with pytest.raises(DriveUnavailableError, match="rate limit"):
        client.list_files(FOLDER_ID)


def test_network_failure_is_reported_as_unavailable():
    def handler(request):
        raise httpx.ConnectError("boom")

    with pytest.raises(DriveUnavailableError, match="Could not reach"):
        make_client(handler).list_files(FOLDER_ID)


def test_non_json_error_body_does_not_crash():
    client = make_client(lambda request: httpx.Response(502, text="<html>bad gateway</html>"))
    with pytest.raises(DriveUnavailableError, match="502"):
        client.list_files(FOLDER_ID)
