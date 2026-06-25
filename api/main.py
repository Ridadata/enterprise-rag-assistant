from fastapi import FastAPI

from api.routes.ask import router as ask_router

app = FastAPI(
    title="Enterprise Data & IT Knowledge RAG Assistant",
    version="0.1.0",
    description="Grounded question answering over enterprise IT and data knowledge.",
)

app.include_router(ask_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

