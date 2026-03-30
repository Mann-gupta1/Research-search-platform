"""
Ingest research paper abstracts from OpenAlex API.

API docs: https://docs.openalex.org/
Uses the works endpoint to fetch papers with abstracts.
"""

import json
import logging
import os
import sys
import time

import requests

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from app.config import settings
from app.db.metadata_store import MetadataStore
from app.db.milvus_client import MilvusClient
from app.services.embedding import EmbeddingService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

OPENALEX_API = "https://api.openalex.org/works"
MAX_ROWS = 50000
BATCH_SIZE = 500
PER_PAGE = 200


def reconstruct_abstract(inverted_index: dict) -> str:
    """Convert OpenAlex inverted abstract index back to plain text."""
    if not inverted_index:
        return ""
    word_positions = []
    for word, positions in inverted_index.items():
        for pos in positions:
            word_positions.append((pos, word))
    word_positions.sort()
    return " ".join(w for _, w in word_positions)


def fetch_papers(max_rows: int = MAX_ROWS) -> list[dict]:
    """Fetch papers from OpenAlex API with pagination."""
    logger.info("Fetching papers from OpenAlex API (max %d)", max_rows)
    papers = []
    cursor = "*"
    polite_email = "research@example.com"

    while len(papers) < max_rows:
        params = {
            "filter": "has_abstract:true,type:article",
            "per_page": min(PER_PAGE, max_rows - len(papers)),
            "cursor": cursor,
            "mailto": polite_email,
            "select": "id,title,publication_date,cited_by_count,concepts,authorships,abstract_inverted_index",
        }

        try:
            resp = requests.get(OPENALEX_API, params=params, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            logger.error("API request failed: %s", e)
            time.sleep(2)
            continue

        results = data.get("results", [])
        if not results:
            break

        for work in results:
            abstract = reconstruct_abstract(
                work.get("abstract_inverted_index", {})
            )
            if not abstract or len(abstract) < 50:
                continue

            work_id = work.get("id", "").split("/")[-1]
            title = work.get("title", "Untitled")
            concepts = work.get("concepts", [])
            tags = [c["display_name"] for c in concepts[:5]] if concepts else []

            papers.append({
                "doc_id": f"paper_{work_id}",
                "title": title or "Untitled",
                "abstract": abstract[:2000],
                "doc_type": "paper",
                "publication_date": work.get("publication_date", ""),
                "citation_count": work.get("cited_by_count", 0) or 0,
                "tags": json.dumps(tags),
                "source_url": work.get("id", ""),
            })

        cursor = data.get("meta", {}).get("next_cursor")
        if not cursor:
            break

        time.sleep(0.1)
        if len(papers) % 1000 == 0:
            logger.info("Fetched %d papers so far...", len(papers))

    logger.info("Fetched %d papers total", len(papers))
    return papers[:max_rows]


def ingest_papers():
    papers = fetch_papers()

    if not papers:
        logger.warning("No papers to ingest")
        return

    embedding_service = EmbeddingService(settings.embedding_model)
    milvus_client = MilvusClient()
    metadata_store = MetadataStore(
        settings.sqlite_db_path,
        database_url=settings.database_url,
    )

    try:
        for start in range(0, len(papers), BATCH_SIZE):
            batch = papers[start : start + BATCH_SIZE]
            abstracts = [p["abstract"] for p in batch]
            embeddings = embedding_service.encode(abstracts)

            doc_ids = [p["doc_id"] for p in batch]
            doc_types = [p["doc_type"] for p in batch]
            emb_list = embeddings.tolist()

            milvus_client.insert(doc_ids, doc_types, emb_list)
            metadata_store.insert_batch(batch)
            logger.info(
                "Ingested paper batch %d-%d / %d",
                start,
                start + len(batch),
                len(papers),
            )

        logger.info("Paper ingestion complete: %d documents", len(papers))
    finally:
        milvus_client.close()
        metadata_store.close()


if __name__ == "__main__":
    ingest_papers()
