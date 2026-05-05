import hashlib
import hmac
import json
import logging

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_auth_service, get_webhook_service
from app.config import Settings, get_settings
from app.logging import RedactingFilter
from app.main import create_app
from app.security import ensure_jwt_secret_strength, rate_limiter


class _AuthServiceStub:
    def __init__(self, vendor_id: int = 1) -> None:
        self.vendor_id = vendor_id

    def decode_token(self, token: str) -> int:
        return self.vendor_id

    async def login(self, email: str, password: str) -> dict:
        return {"vendor_id": self.vendor_id, "token": "stub-token"}

    async def register(self, name: str, email: str, password: str) -> dict:
        return {"vendor_id": self.vendor_id, "token": "stub-token"}


class _WebhookServiceStub:
    async def handle_payload(self, payload: dict) -> dict:
        return {"status": "ok", "messages_received": 1}


def _reset_settings_cache() -> None:
    get_settings.cache_clear()


def test_vendor_scope_enforced() -> None:
    rate_limiter.reset()
    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: _AuthServiceStub(vendor_id=1)
    client = TestClient(app)

    response = client.get("/vendors/2/products", headers={"Authorization": "Bearer stub"})

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "authorization_error"


def test_webhook_signature_verification_rejects_invalid(monkeypatch: pytest.MonkeyPatch) -> None:
    rate_limiter.reset()
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "topsecret")
    _reset_settings_cache()

    app = create_app()
    app.dependency_overrides[get_webhook_service] = lambda: _WebhookServiceStub()
    client = TestClient(app)

    body = json.dumps({"object": "whatsapp_business_account", "entry": []})
    response = client.post(
        "/webhook",
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=invalid",
        },
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_error"


def test_webhook_signature_verification_accepts_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    rate_limiter.reset()
    secret = "topsecret"
    monkeypatch.setenv("WHATSAPP_APP_SECRET", secret)
    _reset_settings_cache()

    app = create_app()
    app.dependency_overrides[get_webhook_service] = lambda: _WebhookServiceStub()
    client = TestClient(app)

    raw_body = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode("utf-8")
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    signature = f"sha256={digest}"

    response = client.post(
        "/webhook",
        data=raw_body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": signature,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_rate_limit_applied(monkeypatch: pytest.MonkeyPatch) -> None:
    rate_limiter.reset()
    monkeypatch.setenv("AUTH_RATE_LIMIT_MAX", "2")
    monkeypatch.setenv("AUTH_RATE_LIMIT_WINDOW_SECONDS", "60")
    _reset_settings_cache()

    app = create_app()
    app.dependency_overrides[get_auth_service] = lambda: _AuthServiceStub(vendor_id=1)
    client = TestClient(app)

    payload = {"email": "owner@acme.com", "password": "strongpassword"}
    first = client.post("/auth/login", json=payload)
    second = client.post("/auth/login", json=payload)
    third = client.post("/auth/login", json=payload)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"]["code"] == "too_many_requests"


def test_jwt_secret_strength_guard_non_dev() -> None:
    with pytest.raises(RuntimeError):
        ensure_jwt_secret_strength(
            Settings(
                APP_ENV="production",
                JWT_SECRET="short-secret",
                JWT_MIN_SECRET_LENGTH=32,
            )
        )


def test_pii_redaction_filter_masks_sensitive_values() -> None:
    filter_ = RedactingFilter()
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="phone=2348012345678 token=abc123 Authorization=Bearer super-secret",
        args=(),
        exc_info=None,
    )

    allowed = filter_.filter(record)

    assert allowed is True
    assert "[REDACTED_PHONE]" in record.msg
    assert "token=[REDACTED]" in record.msg
    assert "Authorization=[REDACTED]" in record.msg
