"""Serve the built React app from the same server as the API."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

DEFAULT_FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"


def mount_frontend(app: FastAPI, directory: Path = DEFAULT_FRONTEND_DIR) -> bool:
    """Mount the built frontend at "/". Returns False when it has not been built.

    In development the Vite server is used instead, so a missing build is fine.
    Call this after the API routes are registered so "/api" keeps priority.
    """
    if not (directory / "index.html").is_file():
        return False
    app.mount("/", StaticFiles(directory=directory, html=True), name="frontend")
    return True
