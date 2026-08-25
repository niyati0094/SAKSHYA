"""Health endpoint and app metadata."""


def test_health_reports_database_connected(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["app"] == "SAKSHYA"


def test_api_root_returns_service_metadata(client):
    response = client.get("/api")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"


def test_root_is_reachable(client):
    """Serves the built frontend when present, service metadata otherwise."""
    assert client.get("/").status_code == 200


def test_unknown_api_path_stays_a_json_404(client):
    """The SPA fallback must not answer a broken endpoint with the app shell."""
    response = client.get("/api/v1/no-such-endpoint")

    assert response.status_code == 404
    assert "text/html" not in response.headers.get("content-type", "")


def test_unknown_client_route_does_not_500(client):
    """A deep link belongs to the client-side router, not to a 500."""
    assert client.get("/learner/evidence").status_code in (200, 404)


def test_openapi_schema_builds(client):
    """Catches malformed response models across every registered route."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/auth/login" in response.json()["paths"]
