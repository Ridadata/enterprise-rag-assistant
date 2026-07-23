import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.corpus import CorpusSummary
from api.security import require_api_key
from api.services.corpus_service import CorpusUnavailable, get_corpus_summary

logger = logging.getLogger(__name__)

router = APIRouter(tags=["corpus"])


@router.get("/corpus/summary", response_model=CorpusSummary, dependencies=[Depends(require_api_key)])
def corpus_summary() -> CorpusSummary:
    try:
        return get_corpus_summary()
    except CorpusUnavailable as exc:
        logger.warning("Corpus summary unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
