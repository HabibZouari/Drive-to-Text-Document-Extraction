"""Extract the folder id from the different shapes of public Drive folder links."""

import re
from urllib.parse import parse_qs, urlparse

from app.drive.errors import InvalidDriveUrlError

_ID = r"[A-Za-z0-9_-]{15,}"
_FOLDER_IN_PATH = re.compile(rf"/folders/({_ID})(?:/|$)")
_ID_ONLY = re.compile(rf"^{_ID}$")
_QUERY_STYLE_PATHS = {"/open", "/folderview"}


def is_valid_folder_id(value: str) -> bool:
    """True if ``value`` looks like a Drive folder id (as returned by extract_folder_id)."""
    return bool(_ID_ONLY.match(value or ""))


def extract_folder_id(url: str) -> str:
    """Return the Drive folder id contained in ``url``.

    Accepted forms:
      https://drive.google.com/drive/folders/<id>[?usp=sharing]
      https://drive.google.com/drive/u/0/folders/<id>
      https://drive.google.com/open?id=<id>
      https://drive.google.com/folderview?id=<id>
    """
    raw = (url or "").strip()
    if not raw:
        raise InvalidDriveUrlError("Paste a Google Drive folder link.")

    parsed = urlparse(raw)
    if parsed.scheme not in ("http", "https") or parsed.hostname != "drive.google.com":
        raise InvalidDriveUrlError(
            "This does not look like a Google Drive link "
            "(expected https://drive.google.com/drive/folders/...)."
        )

    if "/file/d/" in parsed.path:
        raise InvalidDriveUrlError("This is a link to a single file. Paste a folder link instead.")

    match = _FOLDER_IN_PATH.search(parsed.path)
    if match:
        return match.group(1)

    if parsed.path in _QUERY_STYLE_PATHS:
        candidates = parse_qs(parsed.query).get("id", [])
        if candidates and _ID_ONLY.match(candidates[0]):
            return candidates[0]

    raise InvalidDriveUrlError("Could not find a folder id in this link.")
