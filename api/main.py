from fastapi import FastAPI

from api.routes.admin import router as admin_router
from api.routes.ask import router as ask_router
from api.routes.corpus import router as corpus_router

app = FastAPI(
    title="Nexus — Enterprise Knowledge Platform",
    version="0.1.0",
    description="Grounded question answering over enterprise IT and data knowledge.",
)

app.include_router(ask_router)
app.include_router(corpus_router)
app.include_router(admin_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

