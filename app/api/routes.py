from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings, get_settings
from app.drive.client import DriveClient
from app.drive.url import extract_folder_id
from app.extraction.languages import SUPPORTED_LANGUAGES
from app.schemas import FileInfo, FolderRequest, FolderResponse, LanguageInfo

router = APIRouter(prefix="/api")


def get_drive_client(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Iterator[DriveClient]:
    client = DriveClient(settings.google_api_key)
    try:
        yield client
    finally:
        client.close()


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
