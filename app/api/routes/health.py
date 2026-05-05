import logging

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.observability import get_metrics_registry
from app.repositories.base import check_db_connectivity

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
async def ready() -> dict | JSONResponse:
    db_ok = await check_db_connectivity()
    if db_ok:
        return {
            "status": "ready",
            "checks": {"database": "ok"},
        }

    logger.error("readiness_failed | check=database")
    return JSONResponse(
        status_code=503,
        content={
            "status": "not_ready",
            "checks": {"database": "error"},
        },
    )


@router.get("/metrics")
async def metrics() -> dict:
    return {
        "status": "ok",
        "counters": get_metrics_registry().snapshot(),
    }
