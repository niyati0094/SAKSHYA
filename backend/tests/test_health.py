"""Health endpoint and app metadata."""


def test_health_reports_database_connected(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "connected"
    assert body["app"] == "SAKSHYA"


def test_root_returns_service_metadata(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["health"] == "/api/v1/health"


def test_openapi_schema_builds(client):
    """Catches malformed response models across every registered route."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    assert "/api/v1/auth/login" in response.json()["paths"]
