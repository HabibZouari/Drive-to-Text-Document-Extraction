from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import router
from app.frontend import mount_frontend


def make_app(directory) -> tuple[FastAPI, bool]:
    app = FastAPI()
    app.include_router(router)
    return app, mount_frontend(app, directory)


def test_serves_built_frontend_at_root(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Drive to Text</h1>")
    app, mounted = make_app(tmp_path)

    response = TestClient(app).get("/")

    assert mounted is True
    assert response.status_code == 200
    assert "Drive to Text" in response.text


def test_api_routes_keep_priority_over_the_frontend(tmp_path):
    (tmp_path / "index.html").write_text("<h1>Drive to Text</h1>")
    app, _ = make_app(tmp_path)

    response = TestClient(app).get("/api/health")

    assert response.json() == {"status": "ok"}


def test_missing_build_is_not_mounted(tmp_path):
    app, mounted = make_app(tmp_path / "does-not-exist")

    assert mounted is False
    assert TestClient(app).get("/").status_code == 404
