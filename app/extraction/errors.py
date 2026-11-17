"""Errors raised while extracting text. Messages are safe to show to the end user."""


class ExtractionError(Exception):
    """A single file could not be processed. It never aborts the rest of the batch."""
