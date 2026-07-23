import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.admin import AdminSummary
from api.security import require_api_key
from api.services.admin_service import AdminSummaryUnavailable, get_admin_summary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])


@router.get("/admin/summary", response_model=AdminSummary, dependencies=[Depends(require_api_key)])
def admin_summary() -> AdminSummary:
    try:
        return get_admin_summary()
    except AdminSummaryUnavailable as exc:
        logger.warning("Admin summary unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
