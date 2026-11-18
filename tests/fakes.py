"""Small stand-ins for Drive and the worker pool, shared by the job tests."""

from collections.abc import Callable
from concurrent.futures import Executor, Future
from contextlib import contextmanager
from pathlib import Path

from app.drive.client import DriveFile
from app.extraction.models import ExtractionResult, Method


class FakeDrive:
    """Lists a fixed set of files and "downloads" them without any network."""

    def __init__(self, files=None, download_errors=None):
        self.files = files or []
        self.download_errors = download_errors or {}
        self.closed = False

    def list_files(self, folder_id):
        return self.files

    @contextmanager
    def temporary_download(self, file: DriveFile, max_bytes: int):
        if file.id in self.download_errors:
            raise self.download_errors[file.id]
        yield Path(f"/fake/{file.id}")

    def close(self):
        self.closed = True


class SynchronousExecutor(Executor):
    """Runs every task immediately in the calling thread, so tests need no waiting."""

    def submit(self, fn, /, *args, **kwargs):
        future = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # mirror a real executor: errors live in the future
            future.set_exception(exc)
        return future


class DeferredExecutor(Executor):
    """Queues tasks until ``run_all`` is called, to observe the pending state."""

    def __init__(self):
        self.queue: list[Callable[[], None]] = []

    def submit(self, fn, /, *args, **kwargs):
        self.queue.append(lambda: fn(*args, **kwargs))
        return Future()

    def run_all(self):
        while self.queue:
            self.queue.pop(0)()


def make_extractor(errors=None, calls=None):
    """Build an extractor. ``errors`` maps a file id to the exception it should raise."""
    errors = errors or {}

    def extractor(path: Path, kind: str, language: str) -> ExtractionResult:
        file_id = path.name
        if calls is not None:
            calls.append((file_id, kind, language))
        if file_id in errors:
            raise errors[file_id]
        method = Method.PDF_PARSER if kind == "pdf" else Method.OCR
        return ExtractionResult(text=f"text of {file_id}", method=method)

    return extractor


def pdf(file_id, size=100):
    return DriveFile(file_id, f"{file_id}.pdf", "application/pdf", size)


def image(file_id, size=100):
    return DriveFile(file_id, f"{file_id}.png", "image/png", size)
