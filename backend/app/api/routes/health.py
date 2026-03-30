from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "healthy"}


@router.get("/ready")
async def ready_check(request: Request):
    """True when the embedding model is loaded (warm-up finished or after first search)."""
    emb = request.app.state.embedding_service
    return {"embedding_ready": emb.is_ready}
