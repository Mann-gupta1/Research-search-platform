import json
import logging
import os
import time
from typing import Optional

import numpy as np

from app.api.schemas.response import (
    DocumentResult,
    HeatmapCell,
    HeatmapData,
    SearchResponse,
    SubTopic,
)
from app.config import settings
from app.db.metadata_store import MetadataStore
from app.db.milvus_client import MilvusClient
from app.services.clustering import ClusteringService
from app.services.embedding import EmbeddingService
from app.services.trend import TrendService

logger = logging.getLogger(__name__)


class SearchService:
    def __init__(
        self,
        embedding_service: EmbeddingService,
        milvus_client: MilvusClient,
        metadata_store: MetadataStore,
    ):
        self.embedding_service = embedding_service
        self.milvus_client = milvus_client
        self.metadata_store = metadata_store
        self.clustering_service = ClusteringService(n_clusters=settings.clustering_k)
        self.trend_service = TrendService()

    def search(
        self,
        query: str,
        doc_type: str = "both",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_citations: Optional[int] = None,
        tags: Optional[list[str]] = None,
        limit: int = 50,
    ) -> SearchResponse:
        start_time = time.time()
        _dbg = os.getenv("SEARCH_DEBUG", "").lower() in ("1", "true", "yes")

        try:
            query_vector = self.embedding_service.encode_query(query).tolist()
            if _dbg:
                logger.info("SEARCH_DEBUG: embedding OK len=%s", len(query_vector))

            milvus_hits = self.milvus_client.search(
                query_vector=query_vector,
                top_k=min(limit * 2, 200),
                doc_type_filter=doc_type,
            )
            if _dbg:
                logger.info("SEARCH_DEBUG: Milvus OK n_hits=%s", len(milvus_hits))
        except Exception:
            logger.exception("Search failed during embedding or Milvus search")
            raise

        if not milvus_hits:
            return self._empty_response(start_time)

        doc_ids = [h["doc_id"] for h in milvus_hits]
        score_map = {h["doc_id"]: h["score"] for h in milvus_hits}

        metadata_rows = self.metadata_store.get_filtered(
            doc_ids=doc_ids,
            date_from=date_from,
            date_to=date_to,
            min_citations=min_citations,
            tags=tags,
        )

        meta_map = {row["doc_id"]: row for row in metadata_rows}

        results = []
        for doc_id in doc_ids:
            if doc_id not in meta_map:
                continue
            meta = meta_map[doc_id]
            tags = meta.get("tags", "[]")
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except (json.JSONDecodeError, TypeError):
                    tags = []

            results.append(
                DocumentResult(
                    doc_id=doc_id,
                    title=meta["title"],
                    abstract=meta["abstract"],
                    doc_type=meta["doc_type"],
                    publication_date=meta.get("publication_date"),
                    citation_count=meta.get("citation_count", 0),
                    tags=tags,
                    score=score_map.get(doc_id, 0.0),
                )
            )
            if len(results) >= limit:
                break

        if not results:
            return self._empty_response(start_time)

        result_doc_ids = [r.doc_id for r in results]
        vectors_map = self.milvus_client.get_vectors_by_ids(result_doc_ids)

        ordered_embeddings = []
        ordered_abstracts = []
        valid_results = []
        for r in results:
            if r.doc_id in vectors_map:
                ordered_embeddings.append(vectors_map[r.doc_id])
                ordered_abstracts.append(r.abstract)
                valid_results.append(r)

        results = valid_results

        if ordered_embeddings:
            emb_array = np.array(ordered_embeddings, dtype=np.float32)
            cluster_labels, cluster_info = self.clustering_service.assign_labels(
                emb_array, ordered_abstracts
            )

            for i, r in enumerate(results):
                r.cluster_id = cluster_labels[i]

            pub_dates = [r.publication_date or "" for r in results]
            trend_data = self.trend_service.compute_trends(
                cluster_labels, cluster_info, pub_dates
            )
        else:
            cluster_info = []
            trend_data = {"cells": [], "sub_topics": [], "years": [], "velocities": {}}

        clusters = [
            SubTopic(
                cluster_id=ci["cluster_id"],
                label=ci["label"],
                keywords=ci["keywords"],
                doc_count=len(ci["doc_indices"]),
            )
            for ci in cluster_info
        ]

        heatmap = HeatmapData(
            cells=[HeatmapCell(**c) for c in trend_data["cells"]],
            sub_topics=trend_data["sub_topics"],
            years=trend_data["years"],
            velocities=trend_data["velocities"],
        )

        elapsed = (time.time() - start_time) * 1000

        return SearchResponse(
            results=results,
            clusters=clusters,
            heatmap=heatmap,
            total_time_ms=round(elapsed, 2),
        )

    def browse(
        self,
        doc_type: str = "both",
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_citations: Optional[int] = None,
        tags: Optional[list[str]] = None,
        limit: int = 5,
    ) -> SearchResponse:
        """Recent documents from DB + Milvus vectors for clustering (no embedding API call)."""
        start_time = time.time()
        rows = self.metadata_store.list_browse(
            limit=limit,
            doc_type=doc_type,
            date_from=date_from,
            date_to=date_to,
            min_citations=min_citations,
            tags=tags,
        )
        if not rows:
            return self._empty_response(start_time)

        results = []
        for meta in rows:
            doc_id = meta["doc_id"]
            t = meta.get("tags", "[]")
            if isinstance(t, str):
                try:
                    tag_list = json.loads(t)
                except (json.JSONDecodeError, TypeError):
                    tag_list = []
            else:
                tag_list = t or []

            results.append(
                DocumentResult(
                    doc_id=doc_id,
                    title=meta["title"],
                    abstract=meta["abstract"],
                    doc_type=meta["doc_type"],
                    publication_date=meta.get("publication_date"),
                    citation_count=meta.get("citation_count", 0),
                    tags=tag_list,
                    score=1.0,
                )
            )

        result_doc_ids = [r.doc_id for r in results]
        vectors_map = self.milvus_client.get_vectors_by_ids(result_doc_ids)

        ordered_embeddings = []
        ordered_abstracts = []
        valid_results = []
        for r in results:
            if r.doc_id in vectors_map:
                ordered_embeddings.append(vectors_map[r.doc_id])
                ordered_abstracts.append(r.abstract)
                valid_results.append(r)

        results = valid_results

        if ordered_embeddings:
            emb_array = np.array(ordered_embeddings, dtype=np.float32)
            cluster_labels, cluster_info = self.clustering_service.assign_labels(
                emb_array, ordered_abstracts
            )

            for i, r in enumerate(results):
                r.cluster_id = cluster_labels[i]

            pub_dates = [r.publication_date or "" for r in results]
            trend_data = self.trend_service.compute_trends(
                cluster_labels, cluster_info, pub_dates
            )
        else:
            cluster_info = []
            trend_data = {"cells": [], "sub_topics": [], "years": [], "velocities": {}}

        clusters = [
            SubTopic(
                cluster_id=ci["cluster_id"],
                label=ci["label"],
                keywords=ci["keywords"],
                doc_count=len(ci["doc_indices"]),
            )
            for ci in cluster_info
        ]

        heatmap = HeatmapData(
            cells=[HeatmapCell(**c) for c in trend_data["cells"]],
            sub_topics=trend_data["sub_topics"],
            years=trend_data["years"],
            velocities=trend_data["velocities"],
        )

        elapsed = (time.time() - start_time) * 1000

        return SearchResponse(
            results=results,
            clusters=clusters,
            heatmap=heatmap,
            total_time_ms=round(elapsed, 2),
        )

    def _empty_response(self, start_time: float) -> SearchResponse:
        elapsed = (time.time() - start_time) * 1000
        return SearchResponse(
            results=[],
            clusters=[],
            heatmap=HeatmapData(cells=[], sub_topics=[], years=[], velocities={}),
            total_time_ms=round(elapsed, 2),
        )
