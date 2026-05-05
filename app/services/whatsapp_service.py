import logging

import httpx

from app.config import Settings
from app.observability import get_metrics_registry

logger = logging.getLogger(__name__)


class WhatsAppService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_text(self, vendor: dict, to: str, body: str) -> None:
        await self._send(vendor, to, {"type": "text", "text": {"body": body}})

    async def send_buttons(self, vendor: dict, to: str, body: str, buttons: list[dict]) -> None:
        await self._send(
            vendor,
            to,
            {
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": body},
                    "action": {"buttons": [{"type": "reply", "reply": button} for button in buttons]},
                },
            },
        )

    async def _send(self, vendor: dict, to: str, payload: dict) -> None:
        phone_id = vendor.get("whatsapp_phone_number_id")
        token = vendor.get("whatsapp_token")
        if not phone_id or not token:
            logger.warning("Skipped WhatsApp send because vendor credentials are incomplete")
            get_metrics_registry().increment("failures_total")
            return

        url = f"https://graph.facebook.com/{self.settings.whatsapp_api_version}/{phone_id}/messages"
        body = {
            "messaging_product": "whatsapp",
            "to": to,
            **payload,
        }
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                get_metrics_registry().increment("outbound_sends_total")
                logger.info(
                    "whatsapp_send_succeeded | vendor_id=%s | to=%s | type=%s",
                    vendor.get("id"),
                    to,
                    payload.get("type"),
                )
            except Exception:
                get_metrics_registry().increment("failures_total")
                logger.exception(
                    "whatsapp_send_failed | vendor_id=%s | to=%s | type=%s",
                    vendor.get("id"),
                    to,
                    payload.get("type"),
                )
                raise
