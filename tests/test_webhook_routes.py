from fastapi.testclient import TestClient

from app.api.deps import get_webhook_service
from app.config import get_settings
from app.main import create_app
from app.security import rate_limiter


class _CapturingWebhookService:
    def __init__(self) -> None:
        self.received: list[dict] = []

    async def handle_payload(self, payload: dict) -> dict:
        self.received.append(payload)
        message_count = 0
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                message_count += len((change.get("value") or {}).get("messages", []))
        return {"status": "ok", "messages_received": message_count}


def test_webhook_route_accepts_text_and_interactive_payloads(monkeypatch) -> None:
    rate_limiter.reset()
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "")
    get_settings.cache_clear()

    service = _CapturingWebhookService()
    app = create_app()
    app.dependency_overrides[get_webhook_service] = lambda: service
    client = TestClient(app)

    text_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "Customer"}}],
                            "messages": [
                                {
                                    "id": "wamid.text.1",
                                    "from": "2348011111111",
                                    "type": "text",
                                    "text": {"body": "I want to buy this"},
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }
    interactive_payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "changes": [
                    {
                        "value": {
                            "metadata": {"phone_number_id": "phone-1"},
                            "contacts": [{"profile": {"name": "Vendor"}}],
                            "messages": [
                                {
                                    "id": "wamid.int.1",
                                    "from": "2347000000000",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {"id": "btn_approve::2348011111111", "title": "APPROVE"},
                                    },
                                }
                            ],
                        }
                    }
                ]
            }
        ],
    }

    text_response = client.post("/webhook", json=text_payload)
    interactive_response = client.post("/webhook", json=interactive_payload)

    assert text_response.status_code == 200
    assert interactive_response.status_code == 200
    assert text_response.json() == {"status": "ok", "messages_received": 1}
    assert interactive_response.json() == {"status": "ok", "messages_received": 1}
    assert service.received[0]["entry"][0]["changes"][0]["value"]["messages"][0]["type"] == "text"
    assert service.received[1]["entry"][0]["changes"][0]["value"]["messages"][0]["type"] == "interactive"
