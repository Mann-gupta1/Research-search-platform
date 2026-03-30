from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, search
from app.services.embedding import EmbeddingService
from app.db.milvus_client import MilvusClient
from app.db.metadata_store import MetadataStore
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.embedding_service = EmbeddingService(settings.embedding_model)
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
