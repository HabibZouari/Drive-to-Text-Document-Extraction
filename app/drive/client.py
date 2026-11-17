"""Minimal Google Drive API v3 client for public folders (API key, no OAuth)."""

import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import httpx

from app.drive.errors import (
    DriveConfigError,
    DriveError,
    DriveUnavailableError,
    FileTooLargeError,
    FolderNotAccessibleError,
)

DRIVE_API_URL = "https://www.googleapis.com/drive/v3"

# PNG and JPG/JPEG files all report image/jpeg or image/png as their mime type.
SUPPORTED_MIME_TYPES = ("application/pdf", "image/png", "image/jpeg")

_EXTENSIONS = {"application/pdf": ".pdf", "image/png": ".png", "image/jpeg": ".jpg"}

_FOLDER_NOT_ACCESSIBLE = (
    "Folder not found or not public. Share it as 'Anyone with the link' (Viewer)."
)
_FILE_NOT_ACCESSIBLE = (
    "This file cannot be downloaded: it is private, deleted or download-restricted."
)


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    size: int | None

    @property
    def kind(self) -> str:
        """Processing family of the file: "pdf" (PDF parser) or "image" (OCR)."""
        return "pdf" if self.mime_type == "application/pdf" else "image"


class DriveClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None, timeout: float = 15.0):
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=timeout)

    def close(self) -> None:
        self._http.close()

    def list_files(self, folder_id: str) -> list[DriveFile]:
        """List the PDFs and images directly inside a public folder (no recursion)."""
        self._require_api_key()

        mime_filter = " or ".join(f"mimeType = '{m}'" for m in SUPPORTED_MIME_TYPES)
        params = {
            "q": f"'{folder_id}' in parents and trashed = false and ({mime_filter})",
            "fields": "nextPageToken, files(id, name, mimeType, size)",
            "pageSize": 1000,
            "orderBy": "name",
            "key": self._api_key,
        }

        files: list[DriveFile] = []
        while True:
            try:
                response = self._http.get(f"{DRIVE_API_URL}/files", params=params)
            except httpx.HTTPError as exc:
                raise DriveUnavailableError(
                    "Could not reach Google Drive. Check the connection and try again."
                ) from exc
            _raise_for_drive_error(response, _FOLDER_NOT_ACCESSIBLE)
            payload = response.json()
            files.extend(_to_drive_file(item) for item in payload.get("files", []))

            next_page = payload.get("nextPageToken")
            if not next_page:
                return files
            params = {**params, "pageToken": next_page}

    @contextmanager
    def temporary_download(self, file: DriveFile, max_bytes: int) -> Iterator[Path]:
        """Download ``file`` into a temporary directory that is removed on exit.

        The local name is derived from the file id, never from the Drive name,
        so a hostile file name cannot escape the temporary directory.
        """
        with tempfile.TemporaryDirectory(prefix="drive-to-text-") as tmp_dir:
            path = Path(tmp_dir) / f"{file.id}{_EXTENSIONS.get(file.mime_type, '.bin')}"
            self.download_file(file.id, path, max_bytes)
            yield path

    def download_file(self, file_id: str, destination: Path, max_bytes: int) -> None:
        """Stream a public file to ``destination``, refusing anything above ``max_bytes``."""
        self._require_api_key()
        params = {"alt": "media", "key": self._api_key}
        try:
            with self._http.stream(
                "GET", f"{DRIVE_API_URL}/files/{file_id}", params=params
            ) as response:
                if not response.is_success:
                    response.read()
                    _raise_for_drive_error(response, _FILE_NOT_ACCESSIBLE)
                _check_declared_size(response, max_bytes)
                _write_with_limit(response, destination, max_bytes)
        except httpx.HTTPError as exc:
            destination.unlink(missing_ok=True)
            raise DriveUnavailableError(
                "Could not download the file from Google Drive. Try again."
            ) from exc
        except DriveError:
            destination.unlink(missing_ok=True)
            raise

    def _require_api_key(self) -> None:
        if not self._api_key:
            raise DriveConfigError("The server has no GOOGLE_API_KEY configured. See the README.")


def _check_declared_size(response: httpx.Response, max_bytes: int) -> None:
    declared = response.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > max_bytes:
        raise FileTooLargeError(_too_large_message(max_bytes))


def _write_with_limit(response: httpx.Response, destination: Path, max_bytes: int) -> None:
    """Write the body chunk by chunk and stop as soon as the limit is crossed."""
    written = 0
    with destination.open("wb") as out:
        for chunk in response.iter_bytes():
            written += len(chunk)
            if written > max_bytes:
                raise FileTooLargeError(_too_large_message(max_bytes))
            out.write(chunk)


def _too_large_message(max_bytes: int) -> str:
    return f"File is larger than the {max_bytes // (1024 * 1024)} MB limit."


def _to_drive_file(item: dict) -> DriveFile:
    size = item.get("size")
    return DriveFile(
        id=item["id"],
        name=item["name"],
        mime_type=item["mimeType"],
        size=int(size) if size is not None else None,
    )


def _error_reasons(response: httpx.Response) -> set[str]:
    """Collect the machine-readable reasons Google puts in an error body."""
    try:
        error = response.json().get("error", {})
    except ValueError:
        return set()
    if not isinstance(error, dict):
        return set()
    reasons = {e.get("reason") for e in error.get("errors", []) if isinstance(e, dict)}
    reasons |= {d.get("reason") for d in error.get("details", []) if isinstance(d, dict)}
    return {r for r in reasons if r}


def _raise_for_drive_error(response: httpx.Response, not_accessible_message: str) -> None:
    if response.is_success:
        return

    status = response.status_code
    reasons = _error_reasons(response)

    if reasons & {"API_KEY_INVALID", "keyInvalid"}:
        raise DriveConfigError("The Google API key is invalid. Check GOOGLE_API_KEY in .env.")
    if reasons & {"accessNotConfigured", "SERVICE_DISABLED"}:
        raise DriveConfigError("The Google Drive API is not enabled for this API key's project.")
    if status == 429 or reasons & {
        "rateLimitExceeded",
        "userRateLimitExceeded",
        "dailyLimitExceeded",
    }:
        raise DriveUnavailableError("Google Drive rate limit reached. Try again in a moment.")
    if status in (403, 404):
        raise FolderNotAccessibleError(not_accessible_message)
    raise DriveUnavailableError(f"Google Drive returned an unexpected error (HTTP {status}).")
