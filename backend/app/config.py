import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    milvus_host: str = os.getenv("MILVUS_HOST", "localhost")
    milvus_port: int = int(os.getenv("MILVUS_PORT", "19530"))
    sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "./data/metadata.db")
    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    collection_name: str = "documents"
    embedding_dim: int = 384
    default_search_limit: int = 50
    clustering_k: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
