import json
from pathlib import Path

import httpx
import pytest

import app.linkedin.client as client_module
from app.config import Settings
from app.linkedin.auth import LinkedInAuthError
from app.linkedin.client import LinkedInClient, LinkedInNotFoundError, LinkedInRateLimitedError

FIXTURES = Path(__file__).parent / "fixtures"


def _settings() -> Settings:
    s = Settings()
    s.LI_AT = "fake-li-at"
    s.JSESSIONID = "fake-jsessionid"
    return s


def _client_with_transport(monkeypatch, handler) -> LinkedInClient:
    """Build a LinkedInClient whose underlying httpx.Client is wired to a
    MockTransport instead of the real network."""
    mock_client = httpx.Client(base_url="https://www.linkedin.com", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(client_module, "build_authenticated_client", lambda settings: mock_client)
    return LinkedInClient(_settings())


def test_get_profile_returns_parsed_json(monkeypatch):
    fixture = json.loads((FIXTURES / "profile_view_complete.json").read_text())

    def handler(request: httpx.Request) -> httpx.Response:
        assert "profileView" in str(request.url)
        return httpx.Response(200, json=fixture)

    client = _client_with_transport(monkeypatch, handler)
    result = client.get_profile("jane-doe-example")
    assert result["data"]["publicIdentifier"] == "jane-doe-example"


def test_get_profile_404_raises_not_found(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={})

    client = _client_with_transport(monkeypatch, handler)
    with pytest.raises(LinkedInNotFoundError):
        client.get_profile("nonexistent-user")


def test_get_profile_401_raises_auth_error(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={})

    client = _client_with_transport(monkeypatch, handler)
    with pytest.raises(LinkedInAuthError):
        client.get_profile("someone")


def test_get_profile_429_raises_rate_limited(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={})

    client = _client_with_transport(monkeypatch, handler)
    with pytest.raises(LinkedInRateLimitedError):
        client.get_profile("someone")


def test_contact_info_returns_none_on_privacy_restriction(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, json={})

    client = _client_with_transport(monkeypatch, handler)
    assert client.get_contact_info("someone") is None
