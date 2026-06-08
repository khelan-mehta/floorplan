from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.errors import ProblemError, install_error_handlers


def _app() -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)

    @app.get("/boom")
    def boom() -> None:
        raise ProblemError(418, "I am a teapot", "short and stout", extra_field="x")

    return app


def test_problem_error_shape() -> None:
    client = TestClient(_app())
    res = client.get("/boom")
    assert res.status_code == 418
    assert res.headers["content-type"].startswith("application/problem+json")
    body = res.json()
    assert body["title"] == "I am a teapot"
    assert body["status"] == 418
    assert body["detail"] == "short and stout"
    assert body["extra_field"] == "x"
    assert body["instance"] == "/boom"
