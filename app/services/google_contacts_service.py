import asyncio
import json
import logging
import random

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from googleapiclient.errors import HttpError
from googleapiclient.discovery import build

from app.config import Settings
from app.domain.interfaces import GoogleTokenRepository
from app.observability import get_metrics_registry

SCOPES = ["https://www.googleapis.com/auth/contacts"]

logger = logging.getLogger(__name__)


class GoogleContactsService:
    MAX_RETRIES = 3

    def __init__(self, settings: Settings, tokens: GoogleTokenRepository) -> None:
        self.settings = settings
        self.tokens = tokens

    async def _get_credentials(self, vendor_id: int) -> Credentials | None:
        token_json = await self.tokens.get_token_json(vendor_id)
        if not token_json:
            return None

        credentials = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        if credentials.expired and credentials.refresh_token:
            try:
                await asyncio.to_thread(credentials.refresh, GoogleRequest())
                await self.tokens.upsert_token_json(vendor_id, credentials.to_json())
            except Exception:
                get_metrics_registry().increment("failures_total")
                logger.exception("google_contacts_token_refresh_failed | vendor_id=%s", vendor_id)
                return None
        return credentials

    @staticmethod
    def _is_transient_error(exc: Exception) -> bool:
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return True
        if isinstance(exc, HttpError):
            status = getattr(getattr(exc, "resp", None), "status", None)
            return status in {408, 409, 425, 429, 500, 502, 503, 504}
        text = str(exc).lower()
        return any(token in text for token in ("timed out", "timeout", "temporarily", "connection reset", "rate limit"))

    async def _run_with_retries(self, action_name: str, action, *, vendor_id: int):
        last_error: Exception | None = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                return await asyncio.to_thread(action)
            except Exception as exc:
                last_error = exc
                if not self._is_transient_error(exc) or attempt == self.MAX_RETRIES:
                    raise
                delay = (0.25 * (2 ** (attempt - 1))) + random.uniform(0.0, 0.15)
                logger.warning(
                    "google_contacts_retry | vendor_id=%s | action=%s | attempt=%s | delay_seconds=%.2f",
                    vendor_id,
                    action_name,
                    attempt,
                    delay,
                )
                await asyncio.sleep(delay)
        if last_error:
            raise last_error

    def _search_existing_contact_sync(self, credentials: Credentials, whatsapp_number: str) -> bool:
        service = build("people", "v1", credentials=credentials, cache_discovery=False)
        existing = service.people().searchContacts(query=whatsapp_number, readMask="phoneNumbers").execute()
        return bool(existing.get("results"))

    def _create_contact_sync(self, credentials: Credentials, display_name: str, whatsapp_number: str) -> None:
        service = build("people", "v1", credentials=credentials, cache_discovery=False)

        memberships: list[dict] = []
        if self.settings.google_customer_group_resource:
            memberships.append(
                {
                    "contactGroupMembership": {
                        "contactGroupResourceName": self.settings.google_customer_group_resource,
                    }
                }
            )

        body = {
            "names": [{"displayName": display_name}],
            "phoneNumbers": [{"value": whatsapp_number, "type": "other", "label": "WhatsApp"}],
        }
        if memberships:
            body["memberships"] = memberships

        service.people().createContact(body=body).execute()

    async def save_if_new(self, vendor_id: int, display_name: str, whatsapp_number: str) -> bool:
        if not (self.settings.google_client_id and self.settings.google_client_secret):
            return False

        credentials = await self._get_credentials(vendor_id)
        if not credentials:
            return False

        try:
            exists = await self._run_with_retries(
                "search_contact",
                lambda: self._search_existing_contact_sync(credentials, whatsapp_number),
                vendor_id=vendor_id,
            )
            if exists:
                logger.info("google_contacts_contact_exists | vendor_id=%s", vendor_id)
                return True

            await self._run_with_retries(
                "create_contact",
                lambda: self._create_contact_sync(credentials, display_name, whatsapp_number),
                vendor_id=vendor_id,
            )
            logger.info("google_contacts_contact_created | vendor_id=%s", vendor_id)
            return True
        except Exception:
            get_metrics_registry().increment("failures_total")
            logger.exception(
                "Google contacts sync failed | vendor_id=%s | name=%s | number=%s",
                vendor_id,
                display_name,
                whatsapp_number,
            )
            return False
