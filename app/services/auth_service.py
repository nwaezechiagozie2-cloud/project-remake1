from datetime import datetime, timedelta, timezone
import hashlib
import secrets

import bcrypt
import jwt

from app.config import Settings
from app.domain.interfaces import EmailVerificationRepository, VendorRepository
from app.exceptions import AuthenticationError, ConflictError, ResourceNotFoundError, ValidationError

REGISTER_EMAIL_PURPOSE = "REGISTER_EMAIL"
EMAIL_CHANGE_PURPOSE = "EMAIL_CHANGE"


class AuthService:
    def __init__(self, settings: Settings, vendors: VendorRepository, email_tokens: EmailVerificationRepository) -> None:
        self.settings = settings
        self.vendors = vendors
        self.email_tokens = email_tokens

    def _issue_token(self, vendor_id: int) -> str:
        payload = {
            "vendor_id": vendor_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.settings.jwt_ttl_hours),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)

    def _auth_response(self, vendor: dict) -> dict:
        return {
            "vendor_id": vendor["id"],
            "token": self._issue_token(vendor["id"]),
            "email_verified": bool(vendor.get("email_verified_at")),
        }

    def decode_token(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        except Exception as exc:
            raise AuthenticationError("Invalid or expired token") from exc
        vendor_id = payload.get("vendor_id")
        if not isinstance(vendor_id, int):
            raise AuthenticationError("Invalid token payload")
        return vendor_id

    @staticmethod
    def _hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def _check_password(password: str, digest: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8")[:72], digest.encode("utf-8"))

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def _verification_url(self, token: str, purpose: str) -> str:
        return f"/profile?verify_token={token}&purpose={purpose}"

    async def _create_email_token(self, vendor_id: int, email: str, purpose: str) -> dict:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(hours=24)
        await self.email_tokens.create_token(
            vendor_id=vendor_id,
            token_hash=self._token_hash(token),
            purpose=purpose,
            email=email,
            expires_at=expires_at,
        )
        payload = {"email": email, "expires_at": expires_at}
        if self.settings.app_env in {"development", "dev", "local", "test", "testing"}:
            payload["verification_token"] = token
            payload["verification_url"] = self._verification_url(token, purpose)
        return payload

    async def register(self, email: str, password: str) -> dict:
        existing = await self.vendors.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")
        digest = self._hash_password(password)
        name = email.split("@", 1)[0]
        vendor = await self.vendors.create_vendor(name=name, email=email, password_hash=digest)
        verification = await self._create_email_token(vendor["id"], email, REGISTER_EMAIL_PURPOSE)
        return {
            "vendor_id": vendor["id"],
            "token": self._issue_token(vendor["id"]),
            "email_verified": False,
            "email_verification": verification,
        }

    async def login(self, email: str, password: str) -> dict:
        digest = await self.vendors.get_password_hash(email)
        if not digest:
            raise AuthenticationError("Invalid email or password")
        if not self._check_password(password, digest):
            raise AuthenticationError("Invalid email or password")
        vendor = await self.vendors.get_by_email(email)
        if not vendor:
            raise AuthenticationError("Invalid email or password")
        return self._auth_response(vendor)

    async def login_or_create_with_google(self, *, subject_id: str, email: str, email_verified: bool, name: str | None = None) -> dict:
        vendor = await self.vendors.get_by_google_subject_id(subject_id)
        if vendor:
            return self._auth_response(vendor)

        vendor = await self.vendors.get_by_email(email)
        if vendor:
            linked = await self.vendors.link_google_subject(vendor["id"], subject_id, mark_email_verified=email_verified)
            return self._auth_response(linked or vendor)

        random_password = self._hash_password(secrets.token_urlsafe(32))
        vendor = await self.vendors.create_vendor(name=(name or email.split("@", 1)[0])[:255], email=email, password_hash=random_password)
        linked = await self.vendors.link_google_subject(vendor["id"], subject_id, mark_email_verified=email_verified)
        return self._auth_response(linked or vendor)

    async def login_or_create_with_instagram(self, *, instagram_user_id: str, username: str | None = None) -> dict:
        vendor = await self.vendors.get_by_instagram_user_id(instagram_user_id)
        if vendor:
            return self._auth_response(vendor)

        synthetic_email = f"instagram-{instagram_user_id}@instagram.local"
        vendor = await self.vendors.get_by_email(synthetic_email)
        if not vendor:
            random_password = self._hash_password(secrets.token_urlsafe(32))
            vendor = await self.vendors.create_vendor(
                name=(username or f"instagram-{instagram_user_id}")[:255],
                email=synthetic_email,
                password_hash=random_password,
            )
        linked = await self.vendors.link_instagram_user(vendor["id"], instagram_user_id)
        return self._auth_response(linked or vendor)

    async def request_registration_verification(self, email: str) -> dict:
        vendor = await self.vendors.get_by_email(email)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")
        if vendor.get("email_verified_at"):
            return {"email": email, "already_verified": True}
        verification = await self._create_email_token(vendor["id"], vendor["email"], REGISTER_EMAIL_PURPOSE)
        return {"email": email, "already_verified": False, "email_verification": verification}

    async def confirm_registration_email(self, token: str) -> dict:
        consumed = await self.email_tokens.consume_token(self._token_hash(token), REGISTER_EMAIL_PURPOSE)
        if not consumed:
            raise ValidationError("Invalid or expired verification token")
        vendor = await self.vendors.set_email_verified(consumed["vendor_id"])
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")
        return {
            "vendor_id": vendor["id"],
            "email": vendor["email"],
            "email_verified": True,
            "email_verified_at": vendor.get("email_verified_at"),
        }

    async def get_profile(self, vendor_id: int) -> dict:
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")
        return {
            "vendor_id": vendor["id"],
            "name": vendor["name"],
            "email": vendor["email"],
            "email_verified": bool(vendor.get("email_verified_at")),
            "email_verified_at": vendor.get("email_verified_at"),
            "pending_email": vendor.get("pending_email"),
            "providers": {
                "google": bool(vendor.get("google_subject_id")),
                "instagram": bool(vendor.get("instagram_user_id")),
            },
        }

    async def update_profile(self, vendor_id: int, name: str) -> dict:
        vendor = await self.vendors.update_profile(vendor_id, {"name": name})
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")
        return await self.get_profile(vendor_id)

    async def request_email_change(self, vendor_id: int, new_email: str) -> dict:
        vendor = await self.vendors.get_by_id(vendor_id)
        if not vendor:
            raise ResourceNotFoundError("Vendor not found")
        if vendor["email"].lower() == new_email.lower():
            raise ValidationError("New email must be different from current email")
        if await self.vendors.get_by_email(new_email) or await self.vendors.get_by_pending_email(new_email):
            raise ConflictError("Email already registered")
        await self.vendors.set_pending_email(vendor_id, new_email)
        verification = await self._create_email_token(vendor_id, new_email, EMAIL_CHANGE_PURPOSE)
        return {"pending_email": new_email, "email_verification": verification}

    async def confirm_email_change(self, vendor_id: int, token: str) -> dict:
        consumed = await self.email_tokens.consume_token(self._token_hash(token), EMAIL_CHANGE_PURPOSE)
        if not consumed or consumed["vendor_id"] != vendor_id:
            raise ValidationError("Invalid or expired verification token")
        if await self.vendors.get_by_email(consumed["email"]):
            raise ConflictError("Email already registered")
        vendor = await self.vendors.apply_pending_email(vendor_id, consumed["email"])
        if not vendor:
            raise ValidationError("No matching pending email change")
        return await self.get_profile(vendor_id)

    async def change_password(self, vendor_id: int, current_password: str, new_password: str) -> dict:
        digest = await self.vendors.get_password_hash_by_id(vendor_id)
        if not digest:
            raise ResourceNotFoundError("Vendor not found")
        if not self._check_password(current_password, digest):
            raise AuthenticationError("Current password is incorrect")
        await self.vendors.update_password_hash(vendor_id, self._hash_password(new_password))
        return {"status": "updated"}
