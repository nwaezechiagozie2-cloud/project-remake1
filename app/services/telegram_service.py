import logging

import httpx

from app.config import Settings
from app.observability import get_metrics_registry

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send_text(self, vendor: dict, to: str, body: str) -> None:
        token = vendor.get("telegram_bot_token") or self.settings.telegram_bot_token
        if not token:
            logger.warning("Skipped Telegram send because bot token is not configured")
            get_metrics_registry().increment("failures_total")
            return

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": to,
            "text": body,
            "disable_web_page_preview": True,
        }
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                get_metrics_registry().increment("outbound_sends_total")
                logger.info("telegram_send_succeeded | vendor_id=%s | to=%s", vendor.get("id"), to)
            except Exception:
                get_metrics_registry().increment("failures_total")
                logger.exception("telegram_send_failed | vendor_id=%s | to=%s", vendor.get("id"), to)
                raise
