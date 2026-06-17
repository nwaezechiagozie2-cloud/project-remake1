from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from app.config import Settings
from app.domain.interfaces import VendorRepository
from app.exceptions import ValidationError
from app.services.auth_service import AuthService

OAUTH_STATE_TTL_MINUTES = 10
INSTAGRAM_OAUTH_SCOPES = (
    "instagram_business_basic,"
    "instagram_business_manage_messages,"
    "instagram_business_manage_comments,"
    "instagram_business_content_publish,"
    "instagram_business_manage_insights"
)


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
