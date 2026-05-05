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
        "content": {"application/json": {"example": {"error": {"code": "validation_error", "message": "Invalid JSON payload", "details": {"reason": "..."}}}}},
    },
    403: {
        "model": ErrorResponse,
        "description": "Authorization error",
        "content": {"application/json": {"example": {"error": {"code": "authorization_error", "message": "Webhook verification failed", "details": {}}}}},
    },
    429: {
        "model": ErrorResponse,
        "description": "Rate limit exceeded",
        "content": {"application/json": {"example": {"error": {"code": "too_many_requests", "message": "Rate limit exceeded", "details": {}}}}},
    },
}


router = APIRouter(tags=["webhook"], responses=STANDARD_ERROR_RESPONSES)


@router.get("/webhook", dependencies=[Depends(rate_limit_dependency(scope="webhook"))])
async def verify_webhook(request: Request) -> PlainTextResponse:
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    settings = get_settings()
    if mode == "subscribe" and token == settings.whatsapp_verify_token and challenge:
        logger.info("webhook_verification_succeeded")
        return PlainTextResponse(content=challenge, status_code=200)
    get_metrics_registry().increment("failures_total")
    logger.warning("webhook_verification_failed")
    raise AuthorizationError("Webhook verification failed")


@router.post(
    "/webhook",
    response_model=WebhookReceiveResponse,
    dependencies=[Depends(rate_limit_dependency(scope="webhook"))],
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "example": {
                        "object": "whatsapp_business_account",
                        "entry": [
                            {
                                "changes": [
                                    {
                                        "value": {
                                            "metadata": {"phone_number_id": "123456789"},
                                            "contacts": [{"profile": {"name": "Customer"}}],
                                            "messages": [
                                                {
                                                    "id": "wamid.1",
                                                    "from": "2348011111111",
                                                    "type": "text",
                                                    "text": {"body": "I want to buy this"},
                                                }
                                            ],
                                        }
                                    }
                                ]
                            }
                        ],
                    }
                }
            }
        }
    },
)
async def receive_webhook(request: Request, service: WebhookService = Depends(get_webhook_service)) -> WebhookReceiveResponse:
    settings = get_settings()
    raw_body = await request.body()
    logger.info("webhook_receive_started | body_bytes=%s", len(raw_body))
    verify_webhook_signature(
        raw_body=raw_body,
        signature_header=request.headers.get("X-Hub-Signature-256"),
        app_secret=settings.whatsapp_app_secret,
    )

    try:
        payload = json.loads(raw_body.decode("utf-8"))
    except Exception as exc:
        get_metrics_registry().increment("failures_total")
        raise ValidationError("Invalid JSON payload", details={"reason": str(exc)}) from exc
    result = await service.handle_payload(payload)
    get_metrics_registry().increment("webhook_events_total", int(result.get("messages_received", 0)))
    logger.info("webhook_receive_completed | messages_received=%s", result.get("messages_received", 0))
    return WebhookReceiveResponse(**result)
