from contextlib import asynccontextmanager
from urllib.parse import urlparse

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.instagram_webhook import router as instagram_webhook_router
from app.api.routes.profile import router as profile_router
from app.api.routes.telegram_webhook import router as telegram_webhook_router
from app.api.routes.vendor_admin import router as vendor_admin_router
from app.api.routes.webhook import router as webhook_router
from app.config import get_settings
from app.exception_handler import register_exception_handlers
from app.logging import configure_logging
from app.observability import CorrelationIdMiddleware
from app.repositories.base import init_db
from app.security import ensure_jwt_secret_strength


@asynccontextmanager
async def _lifespan(_: FastAPI):
    await init_db()
    yield

def ensure_required_env_vars(settings) -> None:
    if settings.app_env in ("production", "staging"):
        missing = []
        if not settings.whatsapp_verify_token: missing.append("WHATSAPP_VERIFY_TOKEN")
        if not settings.google_client_id: missing.append("GOOGLE_CLIENT_ID")
        if not settings.google_client_secret: missing.append("GOOGLE_CLIENT_SECRET")
        
        if settings.active_llm_provider == "gemini" and not settings.gemini_api_key:
            missing.append("GEMINI_API_KEY")
        if settings.active_llm_provider == "nvidia" and not settings.nvidia_api_key:
            missing.append("NVIDIA_API_KEY")
            
        if missing:
            raise RuntimeError(f"Missing required environment variables for {settings.app_env} mode: {', '.join(missing)}")


def _allowed_cors_origins(settings) -> list[str]:
    origins = []
    frontend_url = (settings.frontend_base_url or "").rstrip("/")
    if frontend_url:
        origins.append(frontend_url)

    if settings.app_env in ("development", "dev", "local", "test", "testing"):
        origins.extend(["http://localhost:3000", "http://127.0.0.1:3000"])

    return list(dict.fromkeys(origin for origin in origins if urlparse(origin).scheme and urlparse(origin).netloc))


def create_app() -> FastAPI:
    settings = get_settings()
    ensure_required_env_vars(settings)
    ensure_jwt_secret_strength(settings)
    configure_logging(debug=settings.app_debug)

    app = FastAPI(title=settings.app_name, debug=settings.app_debug, lifespan=_lifespan)
    register_exception_handlers(app)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_allowed_cors_origins(settings),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(webhook_router)
    app.include_router(instagram_webhook_router)
    app.include_router(telegram_webhook_router)
    app.include_router(vendor_admin_router)
    app.include_router(profile_router)
    return app


app = create_app()
