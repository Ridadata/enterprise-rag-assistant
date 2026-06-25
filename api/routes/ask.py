from fastapi import APIRouter

from api.schemas.qa import AskRequest, AskResponse
from api.services.rag_service import answer_question

router = APIRouter(tags=["qa"])


@router.post("/ask", response_model=AskResponse)
def ask(request: AskRequest) -> AskResponse:
    return answer_question(request)

