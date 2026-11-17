"""Minimal Google Drive API v3 client for public folders (API key, no OAuth)."""

from dataclasses import dataclass

import httpx

from app.drive.errors import (
    DriveConfigError,
    DriveUnavailableError,
    FolderNotAccessibleError,
)

DRIVE_API_URL = "https://www.googleapis.com/drive/v3"

# PNG and JPG/JPEG files all report image/jpeg or image/png as their mime type.
SUPPORTED_MIME_TYPES = ("application/pdf", "image/png", "image/jpeg")


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
        if not self._api_key:
            raise DriveConfigError("The server has no GOOGLE_API_KEY configured. See the README.")

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
            _raise_for_drive_error(response)
            payload = response.json()
            files.extend(_to_drive_file(item) for item in payload.get("files", []))

            next_page = payload.get("nextPageToken")
            if not next_page:
                return files
            params = {**params, "pageToken": next_page}


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


def _raise_for_drive_error(response: httpx.Response) -> None:
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
        raise FolderNotAccessibleError(
            "Folder not found or not public. Share it as 'Anyone with the link' (Viewer)."
        )
    raise DriveUnavailableError(f"Google Drive returned an unexpected error (HTTP {status}).")
