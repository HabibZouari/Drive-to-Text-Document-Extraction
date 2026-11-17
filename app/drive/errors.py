"""Errors raised by the Drive layer. Messages are safe to show to the end user."""


class DriveError(Exception):
    """Base class for every Drive-related failure."""


class InvalidDriveUrlError(DriveError):
    """The pasted text is not a usable Google Drive folder link."""


class FolderNotAccessibleError(DriveError):
    """The folder does not exist or is not shared publicly ("anyone with the link")."""


class DriveConfigError(DriveError):
    """The server-side Drive configuration is wrong (missing or invalid API key, API disabled)."""


class DriveUnavailableError(DriveError):
    """Google Drive could not be reached, or refused the request for a transient reason."""
