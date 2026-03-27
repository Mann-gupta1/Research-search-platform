"""
End-to-end tests for the search platform.

Tests the full search pipeline by mocking the Milvus vector store
and using a real SQLite DB + real Sentence Transformer embeddings.

Run: cd backend && python -m pytest tests/test_e2e.py -v
"""

import json
import os
import sys
import tempfile

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.services.embedding import EmbeddingService
from app.services.clustering import ClusteringService
from app.services.trend import TrendService
from app.db.metadata_store import MetadataStore

SAMPLE_DOCS = [
    {
        "doc_id": "patent_001",
        "title": "Method for thermal management in lithium batteries",
        "abstract": "A novel thermal management system for lithium-ion batteries using phase change materials and heat pipes to maintain optimal operating temperature during rapid charge and discharge cycles in electric vehicles and grid storage applications.",
        "doc_type": "patent",
        "publication_date": "2022-03-15",
        "citation_count": 12,
        "tags": json.dumps(["batteries", "thermal management"]),
        "source_url": "https://example.com/patent/001",
    },
    {
        "doc_id": "paper_001",
        "title": "Deep learning approaches for battery state estimation",
        "abstract": "This paper presents a comprehensive review of deep learning methods for state of charge and state of health estimation in lithium-ion batteries, including LSTM, CNN, and transformer-based architectures applied to battery monitoring systems.",
        "doc_type": "paper",
        "publication_date": "2023-06-01",
        "citation_count": 45,
        "tags": json.dumps(["deep learning", "batteries", "estimation"]),
        "source_url": "https://example.com/paper/001",
    },
    {
        "doc_id": "patent_002",
        "title": "Electrode composition for solid-state batteries",
        "abstract": "An improved electrode composition comprising a novel solid electrolyte material with enhanced ionic conductivity for use in all-solid-state lithium batteries with improved cycle life and energy density for portable electronics.",
        "doc_type": "patent",
        "publication_date": "2021-11-20",
        "citation_count": 8,
        "tags": json.dumps(["solid-state", "electrodes"]),
        "source_url": "https://example.com/patent/002",
    },
    {
        "doc_id": "paper_002",
        "title": "Machine learning for drug discovery: a survey",
        "abstract": "A comprehensive survey of machine learning techniques applied to drug discovery, covering molecular representation learning, virtual screening, de novo drug design, and ADMET property prediction using graph neural networks.",
        "doc_type": "paper",
        "publication_date": "2023-01-10",
        "citation_count": 120,
        "tags": json.dumps(["machine learning", "drug discovery"]),
        "source_url": "https://example.com/paper/002",
    },
    {
        "doc_id": "paper_003",
        "title": "Reinforcement learning for robotic manipulation",
        "abstract": "This work explores the application of model-free reinforcement learning algorithms for dexterous robotic manipulation tasks, demonstrating improved sample efficiency through curriculum learning and sim-to-real transfer techniques.",
        "doc_type": "paper",
        "publication_date": "2022-09-05",
        "citation_count": 30,
        "tags": json.dumps(["reinforcement learning", "robotics"]),
        "source_url": "https://example.com/paper/003",
    },
    {
        "doc_id": "patent_003",
        "title": "Battery charging optimization using neural networks",
        "abstract": "A system and method for optimizing battery charging profiles using artificial neural networks that predict optimal current and voltage curves based on battery health state, temperature, and usage patterns for prolonged battery lifespan.",
        "doc_type": "patent",
        "publication_date": "2023-04-22",
        "citation_count": 5,
        "tags": json.dumps(["neural networks", "batteries", "charging"]),
        "source_url": "https://example.com/patent/003",
    },
    {
        "doc_id": "paper_004",
        "title": "Advances in perovskite solar cell efficiency",
        "abstract": "Recent advances in perovskite solar cell materials and fabrication techniques have pushed power conversion efficiency beyond 25 percent. This paper reviews tandem architectures and stability improvements for commercial deployment.",
        "doc_type": "paper",
        "publication_date": "2024-02-14",
        "citation_count": 88,
        "tags": json.dumps(["solar cells", "perovskite", "energy"]),
        "source_url": "https://example.com/paper/004",
    },
    {
        "doc_id": "patent_004",
        "title": "Fast-charging protocol for electric vehicle batteries",
        "abstract": "A fast-charging protocol for electric vehicle batteries that employs adaptive pulse charging with real-time impedance monitoring to minimize degradation while achieving 80 percent charge in under 15 minutes safely.",
        "doc_type": "patent",
        "publication_date": "2024-01-08",
        "citation_count": 3,
        "tags": json.dumps(["EV", "fast charging", "batteries"]),
        "source_url": "https://example.com/patent/004",
    },
]

embedding_service = None


@pytest.fixture(scope="module")
def emb_service():
    global embedding_service
    if embedding_service is None:
        embedding_service = EmbeddingService()
    return embedding_service


@pytest.fixture(scope="module")
def doc_embeddings(emb_service):
    abstracts = [d["abstract"] for d in SAMPLE_DOCS]
    return emb_service.encode(abstracts)


@pytest.fixture
def metadata_store():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    store = MetadataStore(tmp.name)
    store.insert_batch(SAMPLE_DOCS)
    yield store
    store.close()
    os.unlink(tmp.name)


class TestFullPipeline:
    """Simulates the full search pipeline without Milvus."""

    def test_query_encoding(self, emb_service):
        vec = emb_service.encode_query("lithium battery thermal management")
        assert vec.shape == (384,)
        assert np.linalg.norm(vec) > 0.99  # normalized

    def test_similarity_ranking(self, emb_service, doc_embeddings):
        query_vec = emb_service.encode_query("lithium battery thermal management")
        scores = np.dot(doc_embeddings, query_vec)
        ranked_indices = np.argsort(scores)[::-1]

        top_doc = SAMPLE_DOCS[ranked_indices[0]]
        assert "battery" in top_doc["abstract"].lower() or "lithium" in top_doc["abstract"].lower(), \
            f"Top result should be battery-related, got: {top_doc['title']}"

        print("\n--- Similarity Ranking for 'lithium battery thermal management' ---")
        for i, idx in enumerate(ranked_indices):
            print(f"  {i+1}. [{scores[idx]:.4f}] {SAMPLE_DOCS[idx]['title']}")

    def test_doc_type_filtering(self, emb_service, doc_embeddings):
        query_vec = emb_service.encode_query("machine learning applications")
        scores = np.dot(doc_embeddings, query_vec)

        patent_scores = [(i, scores[i]) for i, d in enumerate(SAMPLE_DOCS) if d["doc_type"] == "patent"]
        paper_scores = [(i, scores[i]) for i, d in enumerate(SAMPLE_DOCS) if d["doc_type"] == "paper"]

        assert len(patent_scores) > 0
        assert len(paper_scores) > 0

    def test_metadata_retrieval(self, metadata_store):
        docs = metadata_store.get_by_ids(["patent_001", "paper_001"])
        assert len(docs) == 2
        for doc in docs:
            assert "title" in doc
            assert "abstract" in doc
            assert len(doc["abstract"]) > 50

    def test_metadata_date_filter(self, metadata_store):
        all_ids = [d["doc_id"] for d in SAMPLE_DOCS]
        results = metadata_store.get_filtered(all_ids, date_from="2023-01-01")
        for r in results:
            assert r["publication_date"] >= "2023-01-01"
        print(f"\n--- Date filter (>=2023): {len(results)} docs ---")
        for r in results:
            print(f"  {r['doc_id']}: {r['publication_date']}")

    def test_metadata_citation_filter(self, metadata_store):
        all_ids = [d["doc_id"] for d in SAMPLE_DOCS]
        results = metadata_store.get_filtered(all_ids, min_citations=30)
        for r in results:
            assert r["citation_count"] >= 30
        print(f"\n--- Citation filter (>=30): {len(results)} docs ---")

    def test_clustering(self, emb_service, doc_embeddings):
        clustering = ClusteringService(n_clusters=3)
        abstracts = [d["abstract"] for d in SAMPLE_DOCS]
        labels, cluster_info = clustering.assign_labels(doc_embeddings, abstracts)

        assert len(labels) == len(SAMPLE_DOCS)
        assert len(cluster_info) >= 1
        assert all(isinstance(ci["label"], str) for ci in cluster_info)

        print("\n--- Clustering Results ---")
        for ci in cluster_info:
            doc_titles = [SAMPLE_DOCS[idx]["title"] for idx in ci["doc_indices"]]
            print(f"  Cluster {ci['cluster_id']}: '{ci['label']}'")
            print(f"    Keywords: {ci['keywords'][:5]}")
            print(f"    Docs: {doc_titles}")

    def test_trend_computation(self, emb_service, doc_embeddings):
        clustering = ClusteringService(n_clusters=3)
        trend_service = TrendService()
        abstracts = [d["abstract"] for d in SAMPLE_DOCS]

        labels, cluster_info = clustering.assign_labels(doc_embeddings, abstracts)
        pub_dates = [d["publication_date"] for d in SAMPLE_DOCS]

        result = trend_service.compute_trends(labels, cluster_info, pub_dates)

        assert "cells" in result
        assert "sub_topics" in result
        assert "years" in result
        assert "velocities" in result
        assert len(result["cells"]) > 0
        assert len(result["sub_topics"]) >= 1
        assert all(isinstance(v, float) for v in result["velocities"].values())

        print("\n--- Trend/Heatmap Data ---")
        print(f"  Sub-topics: {result['sub_topics']}")
        print(f"  Years: {result['years']}")
        print(f"  Velocities: {result['velocities']}")
        print(f"  Heatmap cells ({len(result['cells'])}):")
        for cell in result["cells"]:
            if cell["count"] > 0:
                print(f"    {cell['sub_topic']} | {cell['year']} | count={cell['count']}")

    def test_full_pipeline_response_structure(self, emb_service, doc_embeddings, metadata_store):
        """Simulates the full search response structure."""
        from app.api.schemas.response import (
            DocumentResult, SubTopic, HeatmapCell, HeatmapData, SearchResponse
        )

        query = "battery technology and thermal management"
        query_vec = emb_service.encode_query(query)
        scores = np.dot(doc_embeddings, query_vec)
        ranked_indices = np.argsort(scores)[::-1]

        all_ids = [SAMPLE_DOCS[i]["doc_id"] for i in ranked_indices]
        metadata_rows = metadata_store.get_by_ids(all_ids)
        meta_map = {r["doc_id"]: r for r in metadata_rows}

        results = []
        for idx in ranked_indices:
            doc = SAMPLE_DOCS[idx]
            meta = meta_map.get(doc["doc_id"], doc)
            tags = meta.get("tags", "[]")
            if isinstance(tags, str):
                tags = json.loads(tags)
            results.append(DocumentResult(
                doc_id=doc["doc_id"],
                title=meta["title"],
                abstract=meta["abstract"],
                doc_type=meta["doc_type"],
                publication_date=meta.get("publication_date"),
                citation_count=meta.get("citation_count", 0),
                tags=tags,
                score=float(scores[idx]),
                cluster_id=0,
            ))

        clustering = ClusteringService(n_clusters=3)
        abstracts = [r.abstract for r in results]
        embs = emb_service.encode(abstracts)
        labels, cluster_info = clustering.assign_labels(embs, abstracts)

        for i, r in enumerate(results):
            r.cluster_id = labels[i]

        clusters = [
            SubTopic(
                cluster_id=ci["cluster_id"],
                label=ci["label"],
                keywords=ci["keywords"],
                doc_count=len(ci["doc_indices"]),
            )
            for ci in cluster_info
        ]

        trend_service = TrendService()
        pub_dates = [r.publication_date or "" for r in results]
        trend_data = trend_service.compute_trends(labels, cluster_info, pub_dates)

        heatmap = HeatmapData(
            cells=[HeatmapCell(**c) for c in trend_data["cells"]],
            sub_topics=trend_data["sub_topics"],
            years=trend_data["years"],
            velocities=trend_data["velocities"],
        )

        response = SearchResponse(
            results=results,
            clusters=clusters,
            heatmap=heatmap,
            total_time_ms=42.0,
        )

        assert len(response.results) == len(SAMPLE_DOCS)
        assert len(response.clusters) >= 1
        assert len(response.heatmap.cells) > 0
        assert response.total_time_ms > 0

        response_dict = response.model_dump()
        assert "results" in response_dict
        assert "clusters" in response_dict
        assert "heatmap" in response_dict

        print("\n=== Full Pipeline Response ===")
        print(f"  Results: {len(response.results)} documents")
        print(f"  Clusters: {len(response.clusters)}")
        for c in response.clusters:
            print(f"    - {c.label} ({c.doc_count} docs): {c.keywords[:3]}")
        print(f"  Heatmap: {len(response.heatmap.cells)} cells, {len(response.heatmap.years)} years")
        print(f"  Velocities: {response.heatmap.velocities}")
        print(f"  Top 3 results:")
        for r in response.results[:3]:
            print(f"    [{r.score:.3f}] {r.title} ({r.doc_type})")

        json_str = response.model_dump_json()
        assert len(json_str) > 100
        print(f"\n  JSON response size: {len(json_str)} bytes")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
