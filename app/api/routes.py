from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.api.dependencies import get_drive_client, get_job_manager
from app.config import Settings, get_settings
from app.drive.client import DriveClient
from app.drive.errors import InvalidDriveUrlError
from app.drive.url import extract_folder_id, is_valid_folder_id
from app.extraction.errors import ExtractionError
from app.extraction.languages import SUPPORTED_LANGUAGES, normalize_language
from app.jobs.manager import JobManager
from app.schemas import (
    FileInfo,
    FolderRequest,
    FolderResponse,
    JobCreated,
    JobRequest,
    JobResponse,
    LanguageInfo,
)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/languages", response_model=list[LanguageInfo])
def list_languages():
    """OCR languages the user can choose from."""
    return [LanguageInfo(code=code, label=label) for code, label in SUPPORTED_LANGUAGES.items()]


@router.post("/folders", response_model=FolderResponse)
def list_folder(
    body: FolderRequest,
    drive: Annotated[DriveClient, Depends(get_drive_client)],
):
    """Resolve a public Drive folder link and list the PDFs and images it contains."""
    folder_id = extract_folder_id(body.url)
    files = drive.list_files(folder_id)
    return FolderResponse(
        folder_id=folder_id,
        files=[
            FileInfo(id=f.id, name=f.name, mime_type=f.mime_type, type=f.kind, size=f.size)
            for f in files
        ],
    )


@router.post("/jobs", response_model=JobCreated, status_code=202)
def create_job(
    body: JobRequest,
    drive: Annotated[DriveClient, Depends(get_drive_client)],
    manager: Annotated[JobManager, Depends(get_job_manager)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    """Start processing the selected files of a folder as one batch."""
    if not is_valid_folder_id(body.folder_id):
        raise InvalidDriveUrlError("Invalid folder id.")

    file_ids = list(dict.fromkeys(body.file_ids))  # drop duplicates, keep the order
    if len(file_ids) > settings.max_files_per_batch:
        raise HTTPException(
            400, f"A batch is limited to {settings.max_files_per_batch} files at a time."
        )

    try:
        language = normalize_language(body.language)
    except ExtractionError as exc:
        raise HTTPException(400, str(exc)) from exc

    # Re-list the folder so only real, supported files of this folder can be processed.
    available = {f.id: f for f in drive.list_files(body.folder_id)}
    unknown = [file_id for file_id in file_ids if file_id not in available]
    if unknown:
        raise HTTPException(400, "Some selected files are not in this folder anymore.")

    job_id = manager.create_job([available[file_id] for file_id in file_ids], language)
    return JobCreated(job_id=job_id)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """Current status of a batch. The UI polls this to show live progress."""
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found. It may have expired.")
    return JobResponse.from_job(job)


@router.get("/jobs/{job_id}/export")
def export_job(job_id: str, manager: Annotated[JobManager, Depends(get_job_manager)]):
    """Download the batch results as a JSON file."""
    job = manager.get_job(job_id)
    if job is None:
        raise HTTPException(404, "Job not found. It may have expired.")
    return Response(
        content=JobResponse.from_job(job).model_dump_json(indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="drive-to-text-{job_id[:8]}.json"'},
    )
