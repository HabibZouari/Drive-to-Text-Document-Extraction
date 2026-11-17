"""Errors raised by the Drive layer. Messages are safe to show to the end user."""


class DriveError(Exception):
    """Base class for every Drive-related failure."""


class InvalidDriveUrlError(DriveError):
    """The pasted text is not a usable Google Drive folder link."""
