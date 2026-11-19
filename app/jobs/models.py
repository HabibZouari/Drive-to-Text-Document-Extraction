from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum

from app.drive.client import DriveFile
from app.extraction.models import Method


class FileStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    FAILED = "failed"


class JobStatus(StrEnum):
    RUNNING = "running"
    COMPLETED = "completed"  # every file reached done or failed


@dataclass
class FileResult:
    """State of one file inside a batch."""

    file: DriveFile
    status: FileStatus = FileStatus.PENDING
    method: Method | None = None
    text: str | None = None
    error: str | None = None
    duration_ms: int | None = None


@dataclass
class Job:
    id: str
    language: str
    results: list[FileResult]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def status(self) -> JobStatus:
        finished = {FileStatus.DONE, FileStatus.FAILED}
        if all(result.status in finished for result in self.results):
            return JobStatus.COMPLETED
        return JobStatus.RUNNING

    def count(self, status: FileStatus) -> int:
        return sum(1 for result in self.results if result.status == status)
