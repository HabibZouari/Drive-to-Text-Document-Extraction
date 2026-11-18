import json

import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_drive_client, get_job_manager
from app.config import Settings, get_settings
from app.extraction.errors import ExtractionError
from app.jobs.manager import JobManager
from app.main import app
from tests.fakes import FakeDrive, SynchronousExecutor, image, make_extractor, pdf

FOLDER_ID = "1AbCdEfGhIjKlMnOpQrStUvWxYz012345"


@pytest.fixture
def api():
    drive = FakeDrive([pdf("a"), pdf("bad"), image("c")])
    manager = JobManager(
        drive,
        1024,
        extractor=make_extractor({"bad": ExtractionError("This file is not a valid PDF.")}),
        executor=SynchronousExecutor(),
    )
    settings = Settings(google_api_key="key", max_file_mb=1, max_files_per_batch=3, batch_workers=1)
    app.dependency_overrides[get_drive_client] = lambda: drive
    app.dependency_overrides[get_job_manager] = lambda: manager
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.clear()


def start_job(api, file_ids=("a", "bad", "c"), language="eng", folder_id=FOLDER_ID):
    return api.post(
        "/api/jobs",
        json={"folder_id": folder_id, "file_ids": list(file_ids), "language": language},
    )


def test_create_job_returns_202_and_an_id(api):
    response = start_job(api)
    assert response.status_code == 202
    assert len(response.json()["job_id"]) > 10


def test_polling_shows_counts_and_per_file_results(api):
    job_id = start_job(api).json()["job_id"]

    body = api.get(f"/api/jobs/{job_id}").json()

    assert body["status"] == "completed"
    assert body["counts"] == {"total": 3, "pending": 0, "processing": 0, "done": 2, "failed": 1}
    by_id = {f["id"]: f for f in body["files"]}
    assert by_id["a"]["status"] == "done"
    assert by_id["a"]["method"] == "pdf_parser"
    assert by_id["a"]["text"] == "text of a"
    assert by_id["c"]["method"] == "ocr"
    assert by_id["bad"]["status"] == "failed"
    assert by_id["bad"]["error"] == "This file is not a valid PDF."
    assert by_id["bad"]["text"] is None


def test_export_is_a_downloadable_json_file_with_all_results(api):
    job_id = start_job(api).json()["job_id"]

    response = api.get(f"/api/jobs/{job_id}/export")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith("attachment")
    assert f"drive-to-text-{job_id[:8]}.json" in disposition
    exported = json.loads(response.text)
    assert exported["job_id"] == job_id
    assert [f["status"] for f in exported["files"]] == ["done", "failed", "done"]


def test_duplicate_file_ids_are_processed_once(api):
    job_id = start_job(api, file_ids=["a", "a", "a"]).json()["job_id"]
    assert api.get(f"/api/jobs/{job_id}").json()["counts"]["total"] == 1


def test_language_is_applied_to_the_job(api):
    job_id = start_job(api, language="fra+eng").json()["job_id"]
    assert api.get(f"/api/jobs/{job_id}").json()["language"] == "fra+eng"


def test_unsupported_language_is_a_400(api):
    response = start_job(api, language="klingon")
    assert response.status_code == 400
    assert "Unsupported OCR language" in response.json()["detail"]


def test_file_that_is_not_in_the_folder_is_a_400(api):
    response = start_job(api, file_ids=["a", "not-in-folder"])
    assert response.status_code == 400
    assert "not in this folder" in response.json()["detail"]


def test_malformed_folder_id_is_a_400(api):
    response = start_job(api, folder_id="x")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid folder id."


def test_empty_selection_is_rejected(api):
    assert start_job(api, file_ids=[]).status_code == 422


def test_batch_size_limit_is_enforced(api):
    response = start_job(api, file_ids=["a", "bad", "c", "d"])
    assert response.status_code == 400
    assert "limited to 3 files" in response.json()["detail"]


@pytest.mark.parametrize("path", ["/api/jobs/missing", "/api/jobs/missing/export"])
def test_unknown_job_is_a_404(api, path):
    response = api.get(path)
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]
