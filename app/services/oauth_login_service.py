from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from app.config import Settings
from app.domain.interfaces import VendorRepository
from app.exceptions import ValidationError
from app.services.auth_service import AuthService

OAUTH_STATE_TTL_MINUTES = 10


class OAuthLoginService:
    def __init__(self, settings: Settings, auth: AuthService, vendors: VendorRepository) -> None:
        self.settings = settings
        self.auth = auth
        self.vendors = vendors

    def _issue_state(self, provider: str) -> str:
        payload = {
            "provider": provider,
            "purpose": "oauth_login",
            "exp": datetime.now(timezone.utc) + timedelta(minutes=OAUTH_STATE_TTL_MINUTES),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)

    def _verify_state(self, provider: str, state: str) -> None:
        try:
            payload = jwt.decode(state, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        except Exception as exc:
            raise ValidationError(f"Invalid {provider.title()} OAuth login state") from exc
        if payload.get("provider") != provider or payload.get("purpose") != "oauth_login":
            raise ValidationError(f"Invalid {provider.title()} OAuth login state")

    def _frontend_complete_url(self, auth_payload: dict) -> str:
        params = urlencode(
            {
                "token": auth_payload["token"],
                "vendor_id": str(auth_payload["vendor_id"]),
            }
        )
        return f"{self.settings.frontend_base_url.rstrip('/')}/auth/complete#{params}"

    async def build_google_url(self) -> str:
        if not (self.settings.google_client_id and self.settings.google_client_secret):
            raise ValidationError("Google OAuth login not configured")
        state = self._issue_state("google")
        params = urlencode(
            {
                "client_id": self.settings.google_client_id,
                "redirect_uri": self.settings.google_login_redirect_uri,
                "response_type": "code",
                "scope": "openid email profile",
                "state": state,
                "prompt": "select_account",
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    async def complete_google(self, code: str, state: str) -> str:
        if not code or not state:
            raise ValidationError("Invalid Google OAuth login state")
        self._verify_state("google", state)

        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.settings.google_client_id,
                    "client_secret": self.settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.google_login_redirect_uri,
                },
            )
            if token_response.status_code >= 400:
                raise ValidationError("Google OAuth token exchange failed", details={"body": token_response.text[:500]})
            access_token = token_response.json().get("access_token")
            if not access_token:
                raise ValidationError("Google OAuth token exchange did not return an access token")

            userinfo = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo.status_code >= 400:
                raise ValidationError("Google userinfo lookup failed", details={"body": userinfo.text[:500]})
            profile = userinfo.json()

        subject_id = str(profile.get("sub") or "").strip()
        email = str(profile.get("email") or "").strip()
        if not subject_id or not email:
            raise ValidationError("Google account did not return a usable identity")

        auth_payload = await self.auth.login_or_create_with_google(
            subject_id=subject_id,
            email=email,
            email_verified=bool(profile.get("email_verified")),
            name=profile.get("name"),
        )
        return self._frontend_complete_url(auth_payload)

    async def build_instagram_url(self) -> str:
        if not (self.settings.instagram_client_id and self.settings.instagram_app_secret):
            raise ValidationError("Instagram OAuth login not configured")
        state = self._issue_state("instagram")
        params = urlencode(
            {
                "client_id": self.settings.instagram_client_id,
                "redirect_uri": self.settings.instagram_login_redirect_uri,
                "response_type": "code",
                "scope": "instagram_business_basic,instagram_business_manage_messages",
                "state": state,
            }
        )
        return f"https://www.instagram.com/oauth/authorize?{params}"

    async def complete_instagram(self, code: str, state: str) -> str:
        if not code or not state:
            raise ValidationError("Invalid Instagram OAuth login state")
        self._verify_state("instagram", state)

        async with httpx.AsyncClient(timeout=20) as client:
            token_response = await client.post(
                "https://api.instagram.com/oauth/access_token",
                data={
                    "client_id": self.settings.instagram_client_id,
                    "client_secret": self.settings.instagram_app_secret,
                    "grant_type": "authorization_code",
                    "redirect_uri": self.settings.instagram_login_redirect_uri,
                    "code": code,
                },
            )
            if token_response.status_code >= 400:
                raise ValidationError("Instagram OAuth token exchange failed", details={"body": token_response.text[:500]})
            token_payload = token_response.json()
            access_token = token_payload.get("access_token")
            user_id = str(token_payload.get("user_id") or "").strip()
            if not access_token:
                raise ValidationError("Instagram OAuth token exchange did not return an access token")
            access_token = await self._maybe_exchange_instagram_long_lived_token(access_token)

            username = None
            profile = await client.get(
                f"https://graph.instagram.com/{self.settings.instagram_api_version}/me",
                params={"fields": "id,username", "access_token": access_token},
            )
            if profile.status_code < 400:
                data = profile.json()
                user_id = str(data.get("id") or user_id).strip()
                username = data.get("username")

        if not user_id:
            raise ValidationError("Instagram account did not return a usable identity")

        auth_payload = await self.auth.login_or_create_with_instagram(instagram_user_id=user_id, username=username)
        vendor_id = int(auth_payload["vendor_id"])
        await self.vendors.update_instagram_credentials(
            vendor_id,
            page_id=user_id,
            page_token=access_token,
        )
        await self._subscribe_instagram_messages(user_id, access_token)
        return self._frontend_complete_url(auth_payload)

    async def _maybe_exchange_instagram_long_lived_token(self, access_token: str) -> str:
        params = {
            "grant_type": "ig_exchange_token",
            "client_secret": self.settings.instagram_app_secret,
            "access_token": access_token,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get("https://graph.instagram.com/access_token", params=params)
        if response.status_code >= 400:
            return access_token
        return response.json().get("access_token") or access_token

    async def _subscribe_instagram_messages(self, user_id: str, access_token: str) -> None:
        url = f"https://graph.instagram.com/{self.settings.instagram_api_version}/{user_id}/subscribed_apps"
        params = {
            "subscribed_fields": "messages",
            "access_token": access_token,
        }
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.post(url, params=params)
        if response.status_code >= 400:
            raise ValidationError("Instagram webhook subscription failed", details={"status_code": response.status_code, "body": response.text[:500]})
