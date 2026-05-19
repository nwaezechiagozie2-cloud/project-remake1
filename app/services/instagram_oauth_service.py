import logging
import os
import secrets
from urllib.parse import urlencode, urlparse

import httpx

from app.config import Settings
from app.domain.interfaces import VendorRepository
from app.exceptions import ResourceNotFoundError, ValidationError
from app.observability import get_metrics_registry

logger = logging.getLogger(__name__)


class InstagramOAuthService:
    def __init__(self, settings: Settings, vendors: VendorRepository) -> None:
        self.settings = settings
        self.vendors = vendors
        self._states: dict[str, int] = {}

    def _allow_localhost_oauth(self) -> None:
        parsed_redirect_uri = urlparse(self.settings.instagram_redirect_uri)
        if parsed_redirect_uri.scheme == "http" and parsed_redirect_uri.hostname in {"localhost", "127.0.0.1"}:
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    def _require_config(self) -> None:
        if not (self.settings.instagram_client_id and self.settings.instagram_app_secret):
            raise ValidationError("Instagram OAuth not configured")

    async def build_authorization_url(self, vendor_id: int) -> str:
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")

        self._require_config()
        self._allow_localhost_oauth()

        state = f"{vendor_id}:{secrets.token_hex(16)}"
        self._states[state] = vendor_id

        params = urlencode(
            {
                "client_id": self.settings.instagram_client_id,
                "redirect_uri": self.settings.instagram_redirect_uri,
                "response_type": "code",
                "scope": "instagram_business_basic,instagram_business_manage_messages",
                "state": state,
            }
        )
        return f"https://www.instagram.com/oauth/authorize?{params}"

    async def complete_callback(self, code: str, state: str) -> dict:
        if not code:
            raise ValidationError("Missing authorization code")
        if not state or ":" not in state:
            raise ValidationError("Missing vendor state")

        vendor_id_text, _ = state.split(":", 1)
        try:
            vendor_id = int(vendor_id_text)
        except ValueError as exc:
            raise ValidationError("Invalid vendor state") from exc

        if self._states.pop(state, None) != vendor_id:
            raise ValidationError("Invalid or expired OAuth state")

        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")

        token_response = await self._exchange_code(code)
        access_token = token_response.get("access_token")
        if not access_token:
            raise ValidationError("Instagram OAuth exchange did not return an access token")
        access_token = await self._maybe_exchange_long_lived_token(access_token)

        ig_user = await self._get_ig_user(access_token)
        ig_user_id = str(ig_user.get("id") or "").strip()
        if not ig_user_id:
            raise ValidationError("Could not resolve Instagram user ID from access token")

        updated = await self.vendors.update_instagram_credentials(
            vendor_id,
            page_id=ig_user_id,
            page_token=access_token,
        )
        if not updated:
            raise ResourceNotFoundError("Vendor not found")

        await self._subscribe_messages(ig_user_id, access_token)
        logger.info("instagram_oauth_callback_success | vendor_id=%s", vendor_id)
        return {
            "vendor_id": vendor_id,
            "instagram_page_id": ig_user_id,
            "username": ig_user.get("username"),
        }

    async def _exchange_code(self, code: str) -> dict:
        params = {
            "client_id": self.settings.instagram_client_id,
            "client_secret": self.settings.instagram_app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": self.settings.instagram_redirect_uri,
            "code": code,
        }
        urls = (
            f"https://graph.instagram.com/{self.settings.instagram_api_version}/oauth/access_token",
            "https://api.instagram.com/oauth/access_token",
        )
        errors: list[dict] = []
        async with httpx.AsyncClient(timeout=20) as client:
            for url in urls:
                response = await client.post(url, data=params)
                if response.status_code < 400:
                    return response.json()
                errors.append({"url": url, "status_code": response.status_code, "body": response.text[:500]})
        raise ValidationError("Instagram OAuth exchange failed", details={"attempts": errors})

    async def _maybe_exchange_long_lived_token(self, access_token: str) -> str:
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": self.settings.instagram_app_secret,
            "access_token": access_token,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get("https://graph.instagram.com/access_token", params=params)
        if response.status_code >= 400:
            logger.warning("instagram_long_lived_token_exchange_failed | status=%s", response.status_code)
            return access_token
        return response.json().get("access_token") or access_token

    async def _get_ig_user(self, access_token: str) -> dict:
        url = f"https://graph.instagram.com/{self.settings.instagram_api_version}/me"
        params = {
            "fields": "id,username,account_type",
            "access_token": access_token,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(url, params=params)
        if response.status_code >= 400:
            raise ValidationError("Instagram profile lookup failed", details={"status_code": response.status_code, "body": response.text[:500]})
        return response.json()

    async def _subscribe_messages(self, ig_user_id: str, access_token: str) -> None:
        url = f"https://graph.instagram.com/{self.settings.instagram_api_version}/{ig_user_id}/subscribed_apps"
        params = {
            "subscribed_fields": "messages",
            "access_token": access_token,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, params=params)
        if response.status_code >= 400:
            get_metrics_registry().increment("failures_total")
            raise ValidationError("Instagram webhook subscription failed", details={"status_code": response.status_code, "body": response.text[:500]})
