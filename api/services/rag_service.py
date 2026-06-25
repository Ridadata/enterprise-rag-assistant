from api.schemas.qa import AskRequest, AskResponse
from generation.answer_generator import build_grounded_answer
from retrieval.vector_search import retrieve_relevant_chunks


def answer_question(request: AskRequest) -> AskResponse:
    chunks = retrieve_relevant_chunks(request.question, filters=request.filters)
    return build_grounded_answer(question=request.question, chunks=chunks)

