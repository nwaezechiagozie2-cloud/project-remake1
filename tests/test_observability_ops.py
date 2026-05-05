from fastapi.testclient import TestClient

from app.api.deps import get_google_oauth_service, get_webhook_service
from app.config import get_settings
from app.main import create_app
from app.observability import get_metrics_registry
from app.security import rate_limiter


class _WebhookServiceStub:
    async def handle_payload(self, payload: dict) -> dict:
        return {"status": "ok", "messages_received": 2}


class _OAuthServiceStub:
    async def complete_callback(self, code: str, state: str, authorization_response: str) -> int:
        return 11



def test_correlation_id_header_propagation() -> None:
    rate_limiter.reset()
    get_metrics_registry().reset()

    client = TestClient(create_app())
    response = client.get("/health", headers={"X-Correlation-ID": "cid-123"})

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID") == "cid-123"



def test_correlation_id_generated_when_missing() -> None:
    rate_limiter.reset()
    get_metrics_registry().reset()

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers.get("X-Correlation-ID")



def test_ready_endpoint_reports_db_status(monkeypatch) -> None:
    rate_limiter.reset()
    get_metrics_registry().reset()

    async def _db_ok() -> bool:
        return True

    async def _db_fail() -> bool:
        return False

    monkeypatch.setattr("app.api.routes.health.check_db_connectivity", _db_ok)
    client = TestClient(create_app())
    ok_response = client.get("/ready")

    monkeypatch.setattr("app.api.routes.health.check_db_connectivity", _db_fail)
    fail_response = client.get("/ready")

    assert ok_response.status_code == 200
    assert ok_response.json() == {"status": "ready", "checks": {"database": "ok"}}
    assert fail_response.status_code == 503
    assert fail_response.json() == {"status": "not_ready", "checks": {"database": "error"}}



def test_webhook_route_increments_webhook_metric(monkeypatch) -> None:
    rate_limiter.reset()
    get_metrics_registry().reset()
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "")
    get_settings.cache_clear()

    app = create_app()
    app.dependency_overrides[get_webhook_service] = lambda: _WebhookServiceStub()
    client = TestClient(app)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"changes": [{"value": {"messages": [{"type": "text"}]}}]}],
    }

    response = client.post("/webhook", json=payload)
    metrics = client.get("/metrics")

    assert response.status_code == 200
    assert metrics.status_code == 200
    assert metrics.json()["counters"].get("webhook_events_total", 0) >= 2



def test_oauth_callback_increments_callback_metric() -> None:
    rate_limiter.reset()
    get_metrics_registry().reset()

    app = create_app()
    app.dependency_overrides[get_google_oauth_service] = lambda: _OAuthServiceStub()
    client = TestClient(app)

    callback = client.get("/auth/google/callback?code=abc&state=11:ok")
    metrics = client.get("/metrics")

    assert callback.status_code == 200
    assert metrics.status_code == 200
    assert metrics.json()["counters"].get("oauth_callbacks_total", 0) >= 1
