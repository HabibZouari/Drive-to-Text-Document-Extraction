"""Request and response models of the HTTP API."""

from typing import Literal

from pydantic import BaseModel


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
