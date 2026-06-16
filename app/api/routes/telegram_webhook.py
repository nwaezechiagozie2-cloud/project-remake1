import logging

from fastapi import APIRouter, Depends, Header, Request

from app.api.deps import get_webhook_service
from app.config import get_settings
from app.exceptions import AuthorizationError, ValidationError
from app.observability import get_metrics_registry
from app.schemas.api import ErrorResponse, WebhookReceiveResponse
from app.security import rate_limit_dependency
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

STANDARD_ERROR_RESPONSES = {
    400: {"model": ErrorResponse, "description": "Validation error"},
    403: {"model": ErrorResponse, "description": "Authorization error"},
    429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
}

router = APIRouter(prefix="/telegram", tags=["telegram-webhook"], responses=STANDARD_ERROR_RESPONSES)


@router.post(
    "/webhook",
    response_model=WebhookReceiveResponse,
    dependencies=[Depends(rate_limit_dependency(scope="webhook"))],
)
async def receive_telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookReceiveResponse:
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        get_metrics_registry().increment("failures_total")
        raise AuthorizationError("Telegram webhook verification failed")

    try:
        payload = await request.json()
    except Exception as exc:
        get_metrics_registry().increment("failures_total")
        raise ValidationError("Invalid JSON payload", details={"reason": str(exc)}) from exc

    result = await service.handle_payload({"object": "telegram", "update": payload})
    get_metrics_registry().increment("webhook_events_total", int(result.get("messages_received", 0)))
    logger.info("telegram_webhook_receive_completed | messages_received=%s", result.get("messages_received", 0))
    return WebhookReceiveResponse(**result)
