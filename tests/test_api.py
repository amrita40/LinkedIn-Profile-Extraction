import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import app.services.profile_service as profile_service_module
from app.main import app

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_api_info(client):
    resp = client.get("/api")
    assert resp.status_code == 200
    assert "endpoints" in resp.json()


def test_root_serves_demo_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "text/html" in resp.headers["content-type"]


def test_post_profile_rejects_non_linkedin_url(client):
    resp = client.post("/v1/profile", json={"url": "https://example.com/not-linkedin"})
    assert resp.status_code == 400
    body = resp.json()
    assert body["success"] is False
    assert body["error"]["code"] == "INVALID_LINKEDIN_URL"


def test_post_profile_without_configured_session_returns_503(client, monkeypatch):
    from app.config import get_settings

    get_settings.cache_clear()
    monkeypatch.delenv("LI_AT", raising=False)
    monkeypatch.delenv("JSESSIONID", raising=False)
    get_settings.cache_clear()

    resp = client.post("/v1/profile", json={"url": "https://www.linkedin.com/in/jane-doe-example/"})
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "SERVICE_NOT_CONFIGURED"


class _FakeLinkedInClient:
    """Stands in for app.linkedin.client.LinkedInClient so API tests never
    touch the real network."""

    def __init__(self, settings):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get_profile(self, public_id: str) -> dict:
        return json.loads((FIXTURES / "profile_view_complete.json").read_text())

    def get_contact_info(self, public_id: str):
        return None


def test_post_profile_success(client, monkeypatch):
    from app.config import get_settings

    monkeypatch.setenv("LI_AT", "fake-li-at")
    monkeypatch.setenv("JSESSIONID", "fake-jsessionid")
    get_settings.cache_clear()

    monkeypatch.setattr(profile_service_module, "LinkedInClient", _FakeLinkedInClient)

    resp = client.post("/v1/profile", json={"url": "https://www.linkedin.com/in/jane-doe-example/"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["profile"]["name"] == "Jane Doe"
    assert len(body["data"]["experience"]) == 2
    assert body["metadata"]["status"] == "complete"

    # Second call should be served from cache.
    resp2 = client.post("/v1/profile", json={"url": "https://www.linkedin.com/in/jane-doe-example/"})
    assert resp2.json()["metadata"]["cached"] is True
