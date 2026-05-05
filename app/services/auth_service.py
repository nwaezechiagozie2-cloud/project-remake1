from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import Settings
from app.domain.interfaces import VendorRepository
from app.exceptions import AuthenticationError, ConflictError


class AuthService:
    def __init__(self, settings: Settings, vendors: VendorRepository) -> None:
        self.settings = settings
        self.vendors = vendors

    def _issue_token(self, vendor_id: int) -> str:
        payload = {
            "vendor_id": vendor_id,
            "exp": datetime.now(timezone.utc) + timedelta(hours=self.settings.jwt_ttl_hours),
        }
        return jwt.encode(payload, self.settings.jwt_secret, algorithm=self.settings.jwt_algorithm)

    def decode_token(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[self.settings.jwt_algorithm])
        except Exception as exc:
            raise AuthenticationError("Invalid or expired token") from exc
        vendor_id = payload.get("vendor_id")
        if not isinstance(vendor_id, int):
            raise AuthenticationError("Invalid token payload")
        return vendor_id

    async def register(self, name: str, email: str, password: str) -> dict:
        existing = await self.vendors.get_by_email(email)
        if existing:
            raise ConflictError("Email already registered")
        digest = bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")
        vendor = await self.vendors.create_vendor(name=name, email=email, password_hash=digest)
        return {
            "vendor_id": vendor["id"],
            "token": self._issue_token(vendor["id"]),
        }

    async def login(self, email: str, password: str) -> dict:
        digest = await self.vendors.get_password_hash(email)
        if not digest:
            raise AuthenticationError("Invalid email or password")
        if not bcrypt.checkpw(password.encode("utf-8")[:72], digest.encode("utf-8")):
            raise AuthenticationError("Invalid email or password")
        vendor = await self.vendors.get_by_email(email)
        if not vendor:
            raise AuthenticationError("Invalid email or password")
        return {
            "vendor_id": vendor["id"],
            "token": self._issue_token(vendor["id"]),
        }
