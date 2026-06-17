import logging
import os
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode, urlparse

import httpx
import jwt

from app.config import Settings
from app.domain.interfaces import VendorRepository
from app.exceptions import ResourceNotFoundError, ValidationError
from app.observability import get_metrics_registry
from app.services.auth_service import AuthService
from app.services.oauth_login_service import INSTAGRAM_OAUTH_SCOPES

logger = logging.getLogger(__name__)
INSTAGRAM_CONNECT_STATE_TTL_MINUTES = 10


class InstagramOAuthService:
    def __init__(self, settings: Settings, vendors: VendorRepository, auth: AuthService) -> None:
        self.settings = settings
        self.vendors = vendors
        self.auth = auth

    def _allow_localhost_oauth(self) -> None:
        parsed_redirect_uri = urlparse(self.settings.instagram_redirect_uri)
        if parsed_redirect_uri.scheme == "http" and parsed_redirect_uri.hostname in {"localhost", "127.0.0.1"}:
            os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

    def _require_config(self) -> None:
        if not (self.settings.instagram_client_id and self.settings.instagram_app_secret):
            raise ValidationError("Instagram OAuth not configured")

    def _issue_connect_state(self, vendor_id: int) -> str:
        payload = {
            "provider": "instagram",
            "purpose": "instagram_connect",
            "vendor_id": vendor_id,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=INSTAGRAM_CONNECT_STATE_TTL_MINUTES),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)

    def _decode_connect_state(self, state: str) -> int:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        except Exception as exc:
            raise ValidationError("Invalid or expired OAuth state") from exc
        if payload.get("provider") != "instagram" or payload.get("purpose") != "instagram_connect":
            raise ValidationError("Invalid or expired OAuth state")
        vendor_id = payload.get("vendor_id")
        if not isinstance(vendor_id, int):
            raise ValidationError("Invalid or expired OAuth state")
        return vendor_id

    def _frontend_complete_url(self, auth_payload: dict) -> str:
        params = urlencode(
            {
                "token": auth_payload["token"],
                "vendor_id": str(auth_payload["vendor_id"]),
            }
        )
        return f"{self.settings.frontend_base_url.rstrip('/')}/auth/complete#{params}"

    async def build_authorization_url(self, vendor_id: int) -> str:
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")

        self._require_config()
        self._allow_localhost_oauth()

        params = urlencode(
            {
                "client_id": self.settings.instagram_client_id,
                "redirect_uri": self.settings.instagram_redirect_uri,
                "response_type": "code",
                "scope": INSTAGRAM_OAUTH_SCOPES,
                "force_reauth": "true",
                "state": self._issue_connect_state(vendor_id),
            }
        )
        return f"https://www.instagram.com/oauth/authorize?{params}"

    async def complete_callback(self, code: str, state: str | None = None) -> str:
        if not code:
            raise ValidationError("Missing authorization code")

        token_response = await self._exchange_code(code)
        access_token = token_response.get("access_token")
        if not access_token:
            raise ValidationError("Instagram OAuth exchange did not return an access token")
        access_token = await self._maybe_exchange_long_lived_token(access_token)

        ig_user = await self._get_ig_user(access_token)
        ig_user_id = str(ig_user.get("id") or "").strip()
        if not ig_user_id:
            raise ValidationError("Could not resolve Instagram user ID from access token")

        if not state:
            auth_payload = await self.auth.login_or_create_with_instagram(
                instagram_user_id=ig_user_id,
                username=ig_user.get("username"),
            )
            vendor_id = int(auth_payload["vendor_id"])
            updated = await self.vendors.update_instagram_credentials(
                vendor_id,
                page_id=ig_user_id,
                page_token=access_token,
            )
            if not updated:
                raise ResourceNotFoundError("Vendor not found")
            await self._subscribe_messages(ig_user_id, access_token)
            logger.info("instagram_oauth_login_callback_success | vendor_id=%s", vendor_id)
            return self._frontend_complete_url(auth_payload)

        vendor_id = self._decode_connect_state(state)
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")

        updated = await self.vendors.update_instagram_credentials(
            vendor_id,
            page_id=ig_user_id,
            page_token=access_token,
        )
        if not updated:
            raise ResourceNotFoundError("Vendor not found")

        await self._subscribe_messages(ig_user_id, access_token)
        logger.info("instagram_oauth_callback_success | vendor_id=%s", vendor_id)
        return f"{self.settings.frontend_base_url.rstrip('/')}/settings?instagram=connected"

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
