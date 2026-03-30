from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, search
from app.services.embedding import EmbeddingService
from app.db.milvus_client import MilvusClient
from app.db.metadata_store import MetadataStore
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Defer model load until first /api/search — avoids OOM + port-scan timeout on 512MB hosts
    app.state.embedding_service = EmbeddingService(
        settings.embedding_model, eager=False
    )
    app.state.milvus_client = MilvusClient()
    app.state.metadata_store = MetadataStore(
        settings.sqlite_db_path,
        database_url=settings.database_url,
    )
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
        "search": "POST /api/search",
        "docs": "/docs",
    }


@app.head("/")
async def root_head():
    return Response(status_code=200)
