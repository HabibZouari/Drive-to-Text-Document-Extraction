"""Request and response models of the HTTP API."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.jobs.models import FileStatus, Job, JobStatus


class FolderRequest(BaseModel):
    url: str


class FileInfo(BaseModel):
    id: str
    name: str
    mime_type: str
    type: Literal["pdf", "image"]
    size: int | None


class LanguageInfo(BaseModel):
    code: str
    label: str


class FolderResponse(BaseModel):
    folder_id: str
    files: list[FileInfo]


class JobRequest(BaseModel):
    folder_id: str
    file_ids: list[str] = Field(min_length=1)
    language: str = "eng"


class JobCreated(BaseModel):
    job_id: str


class JobCounts(BaseModel):
    total: int
    pending: int
    processing: int
    done: int
    failed: int


class FileResultInfo(BaseModel):
    id: str
    name: str
    type: Literal["pdf", "image"]
    size: int | None
    status: FileStatus
    method: str | None
    text: str | None
    error: str | None
    duration_ms: int | None


class JobResponse(BaseModel):
    job_id: str
    status: JobStatus
    language: str
    created_at: datetime
    counts: JobCounts
    files: list[FileResultInfo]

    @classmethod
    def from_job(cls, job: Job) -> "JobResponse":
        return cls(
            job_id=job.id,
            status=job.status,
            language=job.language,
            created_at=job.created_at,
            counts=JobCounts(
                total=len(job.results),
                pending=job.count(FileStatus.PENDING),
                processing=job.count(FileStatus.PROCESSING),
                done=job.count(FileStatus.DONE),
                failed=job.count(FileStatus.FAILED),
            ),
            files=[
                FileResultInfo(
                    id=r.file.id,
                    name=r.file.name,
                    type=r.file.kind,
                    size=r.file.size,
                    status=r.status,
                    method=r.method.value if r.method else None,
                    text=r.text,
                    error=r.error,
                    duration_ms=r.duration_ms,
                )
                for r in job.results
            ],
        )
