import logging
import threading

from fastapi import APIRouter, Request

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/ready")
async def ready_check(request: Request):
    emb = request.app.state.embedding_service
    return {"embedding_ready": emb.is_ready}


@router.post("/warm")
async def warm_embedding(request: Request):
    emb = request.app.state.embedding_service
    if emb.is_ready:
        return {
            "embedding_ready": True,
            "message": "Model already loaded; you can search immediately.",
        }

    def _run() -> None:
        try:
            emb.warm()
        except Exception:
            logger.exception("Background /api/warm failed")

    threading.Thread(target=_run, daemon=True, name="api-warm").start()
    return {
        "embedding_ready": False,
        "message": (
            "Warm-up started. Poll GET /api/ready every 10–20s until embedding_ready is true "
            "(first load can take several minutes on small instances), then POST /api/search."
        ),
    }
