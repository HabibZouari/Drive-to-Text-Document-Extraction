"""Minimal Google Drive API v3 client for public folders (API key, no OAuth)."""

from dataclasses import dataclass

import httpx

DRIVE_API_URL = "https://www.googleapis.com/drive/v3"

# PNG and JPG/JPEG files all report image/jpeg or image/png as their mime type.
SUPPORTED_MIME_TYPES = ("application/pdf", "image/png", "image/jpeg")


@dataclass(frozen=True)
class DriveFile:
    id: str
    name: str
    mime_type: str
    size: int | None


class DriveClient:
    def __init__(self, api_key: str, http: httpx.Client | None = None, timeout: float = 15.0):
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=timeout)

    def list_files(self, folder_id: str) -> list[DriveFile]:
        """List the PDFs and images directly inside a public folder (no recursion)."""
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
            response = self._http.get(f"{DRIVE_API_URL}/files", params=params)
            response.raise_for_status()
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
