import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.qa import AskRequest, AskResponse
from api.security import require_api_key
from api.services.rag_service import answer_question
from retrieval.vector_search import RetrievalBackendUnavailable

logger = logging.getLogger(__name__)

router = APIRouter(tags=["qa"])


@router.post("/ask", response_model=AskResponse, dependencies=[Depends(require_api_key)])
def ask(request: AskRequest) -> AskResponse:
    try:
        return answer_question(request)
    except RetrievalBackendUnavailable as exc:
        logger.warning("Retrieval backend unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unhandled error answering question")
        raise HTTPException(status_code=500, detail="Failed to answer the question.") from exc
