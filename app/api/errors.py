"""Translate Drive errors into HTTP responses with a user-facing message."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.drive.errors import (
    DriveConfigError,
    DriveError,
    DriveUnavailableError,
    FolderNotAccessibleError,
    InvalidDriveUrlError,
)

_STATUS_BY_ERROR: dict[type[DriveError], int] = {
    InvalidDriveUrlError: 400,
    FolderNotAccessibleError: 404,
    DriveConfigError: 500,
    DriveUnavailableError: 502,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DriveError)
    async def handle_drive_error(request: Request, exc: DriveError) -> JSONResponse:
        status = _STATUS_BY_ERROR.get(type(exc), 500)
        return JSONResponse(status_code=status, content={"detail": str(exc)})
