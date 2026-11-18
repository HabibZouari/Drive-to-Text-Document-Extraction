"""Objects shared by the route handlers, created once or per request."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends

from app.config import Settings, get_settings
from app.drive.client import DriveClient
from app.jobs.manager import JobManager

_job_manager: JobManager | None = None


def get_drive_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[DriveClient]:
    """A Drive client for the duration of one request."""
    client = DriveClient(settings.google_api_key)
    try:
        yield client
    finally:
        client.close()


def get_job_manager(settings: Annotated[Settings, Depends(get_settings)]) -> JobManager:
    """The single batch runner of the application, created on first use."""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager(
            DriveClient(settings.google_api_key),
            settings.max_file_bytes,
            max_workers=settings.batch_workers,
        )
    return _job_manager


def shutdown_job_manager() -> None:
    global _job_manager
    if _job_manager is not None:
        _job_manager.close()
        _job_manager = None
