import logging
from typing import Optional

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    connections,
    utility,
)

from app.config import settings

logger = logging.getLogger(__name__)


class MilvusClient:
    def __init__(self):
        connections.connect(
            alias="default",
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
        logger.info(
            "Connected to Milvus at %s:%s",
            settings.milvus_host,
            settings.milvus_port,
        )
        self._ensure_collection()

    def _ensure_collection(self):
        if utility.has_collection(settings.collection_name):
            self.collection = Collection(settings.collection_name)
            logger.info("Using existing collection: %s", settings.collection_name)
        else:
            self.collection = self._create_collection()
            logger.info("Created new collection: %s", settings.collection_name)
        self.collection.load()

    def _create_collection(self) -> Collection:
        fields = [
            FieldSchema(
                name="doc_id", dtype=DataType.VARCHAR, is_primary=True, max_length=128
            ),
            FieldSchema(
                name="doc_type", dtype=DataType.VARCHAR, max_length=16
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=settings.embedding_dim,
            ),
        ]
        schema = CollectionSchema(
            fields=fields,
            description="Patent and research paper embeddings",
        )
        collection = Collection(name=settings.collection_name, schema=schema)

        index_params = {
            "metric_type": "IP",
            "index_type": "HNSW",
            "params": {"M": 16, "efConstruction": 256},
        }
        collection.create_index(field_name="embedding", index_params=index_params)
        return collection

    def insert(
        self,
        doc_ids: list[str],
        doc_types: list[str],
        embeddings: list[list[float]],
    ) -> int:
        data = [doc_ids, doc_types, embeddings]
        result = self.collection.insert(data)
        self.collection.flush()
        return result.insert_count

    def search(
        self,
        query_vector: list[float],
        top_k: int = 50,
        doc_type_filter: Optional[str] = None,
    ) -> list[dict]:
        search_params = {"metric_type": "IP", "params": {"ef": 128}}

        expr = None
        if doc_type_filter and doc_type_filter != "both":
            type_val = "patent" if doc_type_filter == "patents" else "paper"
            expr = f'doc_type == "{type_val}"'

        results = self.collection.search(
            data=[query_vector],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=["doc_id", "doc_type"],
        )

        hits = []
        for hit in results[0]:
            hits.append(
                {
                    "doc_id": hit.entity.get("doc_id"),
                    "doc_type": hit.entity.get("doc_type"),
                    "score": float(hit.score),
                }
            )
        return hits

    def get_vectors_by_ids(self, doc_ids: list[str]) -> dict[str, list[float]]:
        if not doc_ids:
            return {}
        id_list = ", ".join(f'"{did}"' for did in doc_ids)
        expr = f"doc_id in [{id_list}]"
        results = self.collection.query(
            expr=expr, output_fields=["doc_id", "embedding"]
        )
        return {r["doc_id"]: r["embedding"] for r in results}

    def close(self):
        connections.disconnect("default")
        logger.info("Disconnected from Milvus")
