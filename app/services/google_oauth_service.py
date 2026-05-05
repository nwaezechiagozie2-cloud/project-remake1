import asyncio
import json
import logging
import os
import secrets
from urllib.parse import urlparse

from google.auth.transport.requests import Request as GoogleRequest
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow

from app.config import Settings
from app.domain.interfaces import GoogleTokenRepository, VendorRepository
from app.exceptions import ResourceNotFoundError, ValidationError
from app.observability import get_metrics_registry

SCOPES = ["https://www.googleapis.com/auth/contacts"]

logger = logging.getLogger(__name__)


class GoogleOAuthService:
    def __init__(self, settings: Settings, vendors: VendorRepository, tokens: GoogleTokenRepository) -> None:
        self.settings = settings
        self.vendors = vendors
        self.tokens = tokens
        self._code_verifiers: dict[str, str] = {}

    def _allow_localhost_oauth(self) -> None:
        parsed_redirect_uri = urlparse(self.settings.google_redirect_uri)
        if parsed_redirect_uri.scheme == "http" and parsed_redirect_uri.hostname in {"localhost", "127.0.0.1"}:
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    def _build_flow(self) -> Flow:
        self._allow_localhost_oauth()
        if not (self.settings.google_client_id and self.settings.google_client_secret):
            raise ValidationError("Google OAuth not configured")

        client_config = {
            "web": {
                "client_id": self.settings.google_client_id,
                "client_secret": self.settings.google_client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.settings.google_redirect_uri],
            }
        }
        flow = Flow.from_client_config(client_config, scopes=SCOPES, autogenerate_code_verifier=True)
        flow.redirect_uri = self.settings.google_redirect_uri
        return flow

    async def build_authorization_url(self, vendor_id: int) -> str:
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")

        flow = self._build_flow()
        oauth_state = f"{vendor_id}:{secrets.token_hex(16)}"
        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
            state=oauth_state,
        )

        code_verifier = getattr(flow, "code_verifier", None)
        if code_verifier:
            self._code_verifiers[state] = code_verifier
        return authorization_url

    async def complete_callback(self, code: str, state: str, authorization_response: str) -> int:
        if not code:
            raise ValidationError("Missing authorization code")
        if not state or ":" not in state:
            raise ValidationError("Missing vendor state")

        vendor_id_text, _ = state.split(":", 1)
        try:
            vendor_id = int(vendor_id_text)
        except ValueError as exc:
            raise ValidationError("Invalid vendor state") from exc

        if not await self.vendors.get_by_id(vendor_id):
            raise ResourceNotFoundError("Vendor not found")

        flow = self._build_flow()
        code_verifier = self._code_verifiers.pop(state, None)
        if code_verifier:
            flow.code_verifier = code_verifier

        try:
            await asyncio.to_thread(flow.fetch_token, authorization_response=authorization_response)
            credentials = flow.credentials
            await self.tokens.upsert_token_json(vendor_id, credentials.to_json())

            if credentials.expired and credentials.refresh_token:
                await asyncio.to_thread(credentials.refresh, GoogleRequest())
                await self.tokens.upsert_token_json(vendor_id, credentials.to_json())
            logger.info("google_oauth_callback_success | vendor_id=%s", vendor_id)
        except Exception as exc:
            get_metrics_registry().increment("failures_total")
            logger.error("google_oauth_callback_failed | vendor_id=%s | reason=%s", vendor_id, str(exc))
            raise ValidationError("Google OAuth callback failed", details={"reason": str(exc)}) from exc

        return vendor_id

    async def get_vendor_oauth_status(self, vendor_id: int) -> dict:
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")

        token_json = await self.tokens.get_token_json(vendor_id)
        if not token_json:
            return {
                "vendor_id": vendor_id,
                "has_credentials": False,
                "status": "not_connected",
                "is_expired": False,
                "has_refresh_token": False,
                "last_error": None,
            }

        try:
            credentials = Credentials.from_authorized_user_info(json.loads(token_json), SCOPES)
        except Exception as exc:
            logger.error("google_oauth_status_invalid_token | vendor_id=%s | reason=%s", vendor_id, str(exc))
            return {
                "vendor_id": vendor_id,
                "has_credentials": True,
                "status": "invalid_credentials",
                "is_expired": True,
                "has_refresh_token": False,
                "last_error": str(exc),
            }

        if credentials.expired and credentials.refresh_token:
            try:
                await asyncio.to_thread(credentials.refresh, GoogleRequest())
                await self.tokens.upsert_token_json(vendor_id, credentials.to_json())
            except Exception as exc:
                get_metrics_registry().increment("failures_total")
                logger.error("google_oauth_refresh_failed | vendor_id=%s | reason=%s", vendor_id, str(exc))
                return {
                    "vendor_id": vendor_id,
                    "has_credentials": True,
                    "status": "refresh_failed",
                    "is_expired": True,
                    "has_refresh_token": True,
                    "last_error": str(exc),
                }

        return {
            "vendor_id": vendor_id,
            "has_credentials": True,
            "status": "connected",
            "is_expired": bool(credentials.expired),
            "has_refresh_token": bool(credentials.refresh_token),
            "last_error": None,
        }
