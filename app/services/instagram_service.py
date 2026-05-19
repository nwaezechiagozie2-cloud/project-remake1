"""
Instagram DM messaging service.

Sends text messages and quick replies via the Instagram Send API
(Meta Graph API). Parallel to WhatsAppService — additive, no shared code.
"""
import logging

import httpx

from app.config import Settings
from app.observability import get_metrics_registry

logger = logging.getLogger(__name__)


class InstagramService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_text(self, vendor: dict, to: str, body: str) -> None:
        """Send a plain text message to an Instagram user (IGSID)."""
        await self._send(vendor, to, {"text": body})

    async def send_quick_replies(
        self, vendor: dict, to: str, body: str, replies: list[dict]
    ) -> None:
        """
        Send a message with quick reply buttons.

        `replies` should be a list of dicts like:
            [{"title": "✅ YES", "payload": "btn_approve::IGSID"}, ...]

        Instagram allows up to 13 quick replies per message.
        """
        quick_replies = [
            {
                "content_type": "text",
                "title": r["title"][:20],  # Instagram caps title at 20 chars
                "payload": r.get("payload") or r.get("id") or r["title"],
            }
            for r in replies[:13]
        ]
        await self._send(vendor, to, {"text": body, "quick_replies": quick_replies})

    async def _send(self, vendor: dict, to: str, message_payload: dict) -> None:
        """Low-level send via Instagram Send API."""
        page_id = vendor.get("instagram_page_id")
        token = vendor.get("instagram_page_token")
        if not page_id or not token:
            logger.warning("Skipped Instagram send because vendor credentials are incomplete")
            get_metrics_registry().increment("failures_total")
            return

        url = f"https://graph.instagram.com/{self.settings.instagram_api_version}/me/messages"
        body = {
            "recipient": {"id": to},
            "message": message_payload,
        }
        headers = {"Authorization": f"Bearer {token}"}
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(url, json=body, headers=headers)
                response.raise_for_status()
                get_metrics_registry().increment("outbound_sends_total")
                logger.info(
                    "instagram_send_succeeded | vendor_id=%s | to=%s",
                    vendor.get("id"),
                    to,
                )
            except Exception:
                get_metrics_registry().increment("failures_total")
                logger.exception(
                    "instagram_send_failed | vendor_id=%s | to=%s",
                    vendor.get("id"),
                    to,
                )
                raise
