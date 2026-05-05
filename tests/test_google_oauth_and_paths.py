import asyncio
import json

import pytest

from app.config import DEFAULT_SQLITE_PATH, Settings
from app.exceptions import ResourceNotFoundError, ValidationError
from app.services.google_oauth_service import GoogleOAuthService


class _VendorRepo:
    async def get_by_id(self, vendor_id: int) -> dict | None:
        if vendor_id == 1:
            return {"id": 1, "name": "Vendor"}
        return None


class _TokenRepo:
    def __init__(self, token_json: str | None = None) -> None:
        self._token_json = token_json

    async def get_token_json(self, vendor_id: int) -> str | None:
        return self._token_json

    async def upsert_token_json(self, vendor_id: int, token_json: str) -> None:
        self._token_json = token_json
        return None


def _service(token_json: str | None = None) -> GoogleOAuthService:
    settings = Settings(
        GOOGLE_CLIENT_ID="client-id",
        GOOGLE_CLIENT_SECRET="client-secret",
        GOOGLE_REDIRECT_URI="http://localhost:8001/auth/google/callback",
    )
    return GoogleOAuthService(settings=settings, vendors=_VendorRepo(), tokens=_TokenRepo(token_json=token_json))


def test_database_default_path_is_project_local() -> None:
    settings = Settings()
    assert settings.database_url == f"sqlite+aiosqlite:///{DEFAULT_SQLITE_PATH.as_posix()}"


def test_google_oauth_authorization_url_builds() -> None:
    url = asyncio.run(_service().build_authorization_url(1))
    assert url.startswith("https://accounts.google.com/o/oauth2/")
    assert "client_id=client-id" in url


def test_google_oauth_vendor_not_found() -> None:
    with pytest.raises(ResourceNotFoundError):
        asyncio.run(_service().build_authorization_url(999))


def test_google_oauth_callback_invalid_state() -> None:
    with pytest.raises(ValidationError):
        asyncio.run(
            _service().complete_callback(
                code="abc",
                state="bad-state",
                authorization_response="http://localhost:8001/auth/google/callback?code=abc&state=bad-state",
            )
        )


def test_google_oauth_status_not_connected() -> None:
    status = asyncio.run(_service().get_vendor_oauth_status(1))
    assert status["vendor_id"] == 1
    assert status["status"] == "not_connected"
    assert status["has_credentials"] is False


def test_google_oauth_status_connected_when_token_present() -> None:
    token_json = json.dumps(
        {
            "token": "access-token",
            "refresh_token": "refresh-token",
            "token_uri": "https://oauth2.googleapis.com/token",
            "client_id": "client-id",
            "client_secret": "client-secret",
            "scopes": ["https://www.googleapis.com/auth/contacts"],
            "expiry": "2099-01-01T00:00:00Z",
        }
    )
    status = asyncio.run(_service(token_json=token_json).get_vendor_oauth_status(1))
    assert status["status"] == "connected"
    assert status["has_credentials"] is True
    assert status["is_expired"] is False


def test_google_oauth_status_invalid_credentials() -> None:
    status = asyncio.run(_service(token_json="{bad-json").get_vendor_oauth_status(1))
    assert status["status"] == "invalid_credentials"
    assert status["has_credentials"] is True
    assert status["last_error"] is not None
