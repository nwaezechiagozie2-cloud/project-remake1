import uuid

from fastapi.testclient import TestClient

from app.api.deps import get_google_oauth_service
from app.main import create_app
from app.security import rate_limiter


class _OAuthServiceStub:
    async def build_authorization_url(self, vendor_id: int) -> str:
        return f"https://accounts.google.com/o/oauth2/auth?state={vendor_id}:stub"

    async def complete_callback(self, code: str, state: str, authorization_response: str) -> int:
        return 7


def test_auth_register_conflict_and_login_failure() -> None:
    rate_limiter.reset()
    client = TestClient(create_app())

    email = f"vendor-{uuid.uuid4().hex[:8]}@example.com"
    register_payload = {
        "name": "Acme Vendor",
        "email": email,
        "password": "supersecurepassword",
    }

    first = client.post("/auth/register", json=register_payload)
    second = client.post("/auth/register", json=register_payload)
    bad_login = client.post("/auth/login", json={"email": email, "password": "wrongpassword"})

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"
    assert bad_login.status_code == 401
    assert bad_login.json()["error"]["code"] == "authentication_error"


def test_auth_google_callback_missing_and_invalid_state() -> None:
    rate_limiter.reset()
    client = TestClient(create_app())

    missing = client.get("/auth/google/callback")
    invalid = client.get("/auth/google/callback?code=abc&state=bad-state")

    assert missing.status_code == 400
    assert missing.json()["error"]["code"] == "validation_error"
    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "validation_error"


def test_auth_google_routes_success_with_override() -> None:
    rate_limiter.reset()
    app = create_app()
    app.dependency_overrides[get_google_oauth_service] = lambda: _OAuthServiceStub()
    client = TestClient(app)

    redirect = client.get("/auth/google?vendor_id=4", follow_redirects=False)
    callback = client.get("/auth/google/callback?code=abc&state=7:ok")

    assert redirect.status_code in {302, 307}
    assert "accounts.google.com" in redirect.headers.get("location", "")
    assert callback.status_code == 200
    assert "vendor <code>7</code>" in callback.text
