"""
Instagram webhook endpoint.

Handles webhook verification (GET) and incoming DM events (POST)
from the Instagram Messaging API. Separate from the WhatsApp webhook
because it uses a different Meta App with its own app secret.
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import PlainTextResponse
import json
import logging

from app.api.deps import get_webhook_service
from app.config import get_settings
from app.exceptions import AuthorizationError, ValidationError
from app.observability import get_metrics_registry
from app.schemas.api import ErrorResponse, WebhookReceiveResponse
from app.security import rate_limit_dependency, verify_webhook_signature
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)

STANDARD_ERROR_RESPONSES = {
    400: {
        "model": ErrorResponse,
        "description": "Validation error",
    },
    403: {
        "model": ErrorResponse,
        "description": "Authorization error",
    },
    429: {
        "model": ErrorResponse,
        "description": "Rate limit exceeded",
    },
}

router = APIRouter(prefix="/instagram", tags=["instagram-webhook"], responses=STANDARD_ERROR_RESPONSES)


@router.get("/webhook", dependencies=[Depends(rate_limit_dependency(scope="webhook"))])
async def verify_instagram_webhook(request: Request) -> PlainTextResponse:
    """
    Instagram webhook verification.

    Meta sends a GET request with hub.mode, hub.verify_token, and hub.challenge
    when you configure the webhook URL in the Instagram API dashboard.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    settings = get_settings()
    if mode == "subscribe" and token == settings.instagram_verify_token and challenge:
        logger.info("instagram_webhook_verification_succeeded")
        return PlainTextResponse(content=challenge, status_code=200)

    get_metrics_registry().increment("failures_total")
    logger.warning("instagram_webhook_verification_failed")
    raise AuthorizationError("Instagram webhook verification failed")


@router.post(
    "/webhook",
    response_model=WebhookReceiveResponse,
    dependencies=[Depends(rate_limit_dependency(scope="webhook"))],
)
async def receive_instagram_webhook(
    request: Request,
    service: WebhookService = Depends(get_webhook_service),
) -> WebhookReceiveResponse:
    """
    Receive incoming Instagram DM events.

    Meta signs the payload with X-Hub-Signature-256 using the
    Instagram App Secret (separate from WhatsApp App Secret).
    """
    settings = get_settings()
    raw_body = await request.body()
    logger.info("instagram_webhook_receive_started | body_bytes=%s", len(raw_body))

    verify_webhook_signature(
        raw_body=raw_body,
        signature_header=request.headers.get("X-Hub-Signature-256"),
        app_secret=settings.instagram_app_secret,
    )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        get_metrics_registry().increment("failures_total")
        raise ValidationError("Invalid JSON payload", details={"reason": str(exc)}) from exc

    result = await service.handle_payload(payload)
    get_metrics_registry().increment("webhook_events_total", int(result.get("messages_received", 0)))
    logger.info("instagram_webhook_receive_completed | messages_received=%s", result.get("messages_received", 0))
    return WebhookReceiveResponse(**result)
