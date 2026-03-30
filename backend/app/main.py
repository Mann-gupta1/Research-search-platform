import logging
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, search
from app.services.embedding import EmbeddingService
from app.db.milvus_client import MilvusClient
from app.db.metadata_store import MetadataStore
from app.config import settings

logger = logging.getLogger(__name__)


def _warm_embedding(app: FastAPI) -> None:
    try:
        app.state.embedding_service.warm()
        logger.info("Embedding model warm-up finished")
    except Exception:
        logger.exception("Embedding model warm-up failed; first /api/search may error")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Defer model load until warm-up thread or first /api/search — keeps port binding fast on Render
    app.state.embedding_service = EmbeddingService(
        settings.embedding_model, eager=False
    )
    app.state.milvus_client = MilvusClient()
    app.state.metadata_store = MetadataStore(
        settings.sqlite_db_path,
        database_url=settings.database_url,
    )
    # Default off: background load + Milvus/DB often exceeds Render free 512MB → OOM → 502.
    # Set WARM_EMBEDDING_ON_STARTUP=1 on instances with ≥1GB RAM if you want faster first search.
    if os.getenv("WARM_EMBEDDING_ON_STARTUP", "0").lower() in ("1", "true", "yes"):
        threading.Thread(
            target=_warm_embedding,
            args=(app,),
            daemon=True,
            name="embed-warmup",
        ).start()
    yield
    app.state.milvus_client.close()
    app.state.metadata_store.close()


app = FastAPI(
    title="Research Search Platform",
    description="Semantic search over patents and research papers",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/")
async def root():
    """Render and load balancers often probe GET /; API lives under /api."""
    return {
        "service": "research-search-platform",
        "health": "/api/health",
        "ready": "/api/ready",
        "search": "POST /api/search",
        "docs": "/docs",
        "note": "First search may take 1–3 min on cold start; use POST with JSON or upgrade RAM.",
    }


@app.head("/")
async def root_head():
    return Response(status_code=200)
