from app.main import app


def test_openapi_lists_core_endpoints() -> None:
    spec = app.openapi()
    paths = spec["paths"]
    for expected in [
        "/auth/login",
        "/auth/register",
        "/projects",
        "/projects/{project_id}/boundary",
        "/projects/{project_id}/program",
        "/projects/{project_id}/generate",
        "/plans/{plan_id}",
        "/plans/{plan_a}/diff/{plan_b}",
        "/plans/{plan_id}/export",
        "/projects/{project_id}/shares",
        "/shared/{token}",
        "/plans/{plan_id}/approval",
        "/projects/{project_id}/audit",
        "/jobs/{job_id}",
        "/health",
    ]:
        assert expected in paths, f"missing {expected}"
