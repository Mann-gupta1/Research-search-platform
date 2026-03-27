"""
Integration tests for the search platform backend.

Requires Milvus to be running. Use docker-compose to start services first:
    docker-compose up -d milvus-standalone

Run tests:
    cd backend && python -m pytest tests/ -v
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
        "doc_id": "test_patent_001",
        "title": "Method for thermal management in lithium batteries",
        "abstract": "A novel thermal management system for lithium-ion batteries using phase change materials and heat pipes to maintain optimal operating temperature during rapid charge and discharge cycles.",
        "doc_type": "patent",
        "publication_date": "2022-03-15",
        "citation_count": 12,
        "tags": json.dumps(["batteries", "thermal management"]),
        "source_url": "https://example.com/patent/001",
    },
    {
        "doc_id": "test_paper_001",
        "title": "Deep learning approaches for battery state estimation",
        "abstract": "This paper presents a comprehensive review of deep learning methods for state of charge and state of health estimation in lithium-ion batteries, including LSTM, CNN, and transformer-based architectures.",
        "doc_type": "paper",
        "publication_date": "2023-06-01",
        "citation_count": 45,
        "tags": json.dumps(["deep learning", "batteries", "estimation"]),
        "source_url": "https://example.com/paper/001",
    },
    {
        "doc_id": "test_patent_002",
        "title": "Electrode composition for solid-state batteries",
        "abstract": "An improved electrode composition comprising a novel solid electrolyte material with enhanced ionic conductivity for use in all-solid-state lithium batteries with improved cycle life.",
        "doc_type": "patent",
        "publication_date": "2021-11-20",
        "citation_count": 8,
        "tags": json.dumps(["solid-state", "electrodes"]),
        "source_url": "https://example.com/patent/002",
    },
    {
        "doc_id": "test_paper_002",
        "title": "Machine learning for drug discovery: a survey",
        "abstract": "A comprehensive survey of machine learning techniques applied to drug discovery, covering molecular representation learning, virtual screening, de novo drug design, and ADMET property prediction.",
        "doc_type": "paper",
        "publication_date": "2023-01-10",
        "citation_count": 120,
        "tags": json.dumps(["machine learning", "drug discovery"]),
        "source_url": "https://example.com/paper/002",
    },
    {
        "doc_id": "test_paper_003",
        "title": "Reinforcement learning for robotic manipulation",
        "abstract": "This work explores the application of model-free reinforcement learning algorithms for dexterous robotic manipulation tasks, demonstrating improved sample efficiency through curriculum learning.",
        "doc_type": "paper",
        "publication_date": "2022-09-05",
        "citation_count": 30,
        "tags": json.dumps(["reinforcement learning", "robotics"]),
        "source_url": "https://example.com/paper/003",
    },
]


class TestEmbeddingService:
    def test_encode_single(self):
        service = EmbeddingService()
        vec = service.encode_query("lithium battery thermal management")
        assert vec.shape == (384,)
        assert np.isfinite(vec).all()

    def test_encode_batch(self):
        service = EmbeddingService()
        texts = ["hello world", "machine learning", "battery technology"]
        embeddings = service.encode(texts)
        assert embeddings.shape == (3, 384)

    def test_similar_queries_close(self):
        service = EmbeddingService()
        v1 = service.encode_query("lithium battery")
        v2 = service.encode_query("lithium-ion battery cell")
        v3 = service.encode_query("recipe for chocolate cake")
        sim_related = float(np.dot(v1, v2))
        sim_unrelated = float(np.dot(v1, v3))
        assert sim_related > sim_unrelated


class TestMetadataStore:
    def setup_method(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.store = MetadataStore(self.tmp.name)

    def teardown_method(self):
        self.store.close()
        os.unlink(self.tmp.name)

    def test_insert_and_retrieve(self):
        self.store.insert_batch(SAMPLE_DOCS)
        results = self.store.get_by_ids(["test_patent_001", "test_paper_001"])
        assert len(results) == 2
        titles = {r["title"] for r in results}
        assert "Method for thermal management in lithium batteries" in titles

    def test_filter_by_date(self):
        self.store.insert_batch(SAMPLE_DOCS)
        results = self.store.get_filtered(
            doc_ids=[d["doc_id"] for d in SAMPLE_DOCS],
            date_from="2023-01-01",
        )
        assert all(r["publication_date"] >= "2023-01-01" for r in results)

    def test_filter_by_citations(self):
        self.store.insert_batch(SAMPLE_DOCS)
        results = self.store.get_filtered(
            doc_ids=[d["doc_id"] for d in SAMPLE_DOCS],
            min_citations=40,
        )
        assert all(r["citation_count"] >= 40 for r in results)

    def test_count(self):
        self.store.insert_batch(SAMPLE_DOCS)
        assert self.store.count() == 5


class TestClusteringService:
    def test_cluster_documents(self):
        service = EmbeddingService()
        clustering = ClusteringService(n_clusters=2)

        abstracts = [d["abstract"] for d in SAMPLE_DOCS]
        embeddings = service.encode(abstracts)
        clusters = clustering.cluster_documents(embeddings, abstracts, n_clusters=2)

        assert len(clusters) >= 1
        all_indices = []
        for c in clusters:
            assert "label" in c
            assert "keywords" in c
            assert "doc_indices" in c
            all_indices.extend(c["doc_indices"])
        assert sorted(all_indices) == list(range(len(SAMPLE_DOCS)))

    def test_single_document(self):
        clustering = ClusteringService()
        embeddings = np.random.randn(1, 384).astype(np.float32)
        clusters = clustering.cluster_documents(embeddings, ["test abstract"])
        assert len(clusters) == 1


class TestTrendService:
    def test_compute_trends(self):
        trend_service = TrendService()
        cluster_labels = [0, 0, 1, 1, 0]
        cluster_info = [
            {"cluster_id": 0, "label": "Batteries", "keywords": ["battery"], "doc_indices": [0, 1, 4]},
            {"cluster_id": 1, "label": "ML Applications", "keywords": ["ml"], "doc_indices": [2, 3]},
        ]
        pub_dates = ["2022-03-15", "2023-06-01", "2021-11-20", "2023-01-10", "2022-09-05"]

        result = trend_service.compute_trends(cluster_labels, cluster_info, pub_dates)
        assert "cells" in result
        assert "sub_topics" in result
        assert "years" in result
        assert "velocities" in result
        assert len(result["sub_topics"]) == 2
        assert len(result["years"]) >= 2

    def test_empty_dates(self):
        trend_service = TrendService()
        result = trend_service.compute_trends([0], [{"cluster_id": 0, "label": "X", "keywords": [], "doc_indices": [0]}], [""])
        assert result["cells"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
