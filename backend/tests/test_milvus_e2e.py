"""
End-to-end test with real Milvus.
Requires Milvus running on localhost:19530 (via docker-compose).

Run: cd backend && python -m pytest tests/test_milvus_e2e.py -v -s
"""

import json
import os
import sys
import tempfile
import time

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.config import settings
from app.services.embedding import EmbeddingService
from app.services.search import SearchService
from app.db.milvus_client import MilvusClient
from app.db.metadata_store import MetadataStore

TEST_COLLECTION = "test_documents"

SAMPLE_DOCS = [
    {
        "doc_id": "mtest_patent_001",
        "title": "Method for thermal management in lithium batteries",
        "abstract": "A novel thermal management system for lithium-ion batteries using phase change materials and heat pipes to maintain optimal operating temperature during rapid charge and discharge cycles.",
        "doc_type": "patent",
        "publication_date": "2022-03-15",
        "citation_count": 12,
        "tags": json.dumps(["batteries", "thermal management"]),
        "source_url": "https://example.com/patent/001",
    },
    {
        "doc_id": "mtest_paper_001",
        "title": "Deep learning approaches for battery state estimation",
        "abstract": "This paper presents a comprehensive review of deep learning methods for state of charge and state of health estimation in lithium-ion batteries, including LSTM, CNN, and transformer-based architectures.",
        "doc_type": "paper",
        "publication_date": "2023-06-01",
        "citation_count": 45,
        "tags": json.dumps(["deep learning", "batteries"]),
        "source_url": "https://example.com/paper/001",
    },
    {
        "doc_id": "mtest_patent_002",
        "title": "Electrode composition for solid-state batteries",
        "abstract": "An improved electrode composition comprising a novel solid electrolyte material with enhanced ionic conductivity for use in all-solid-state lithium batteries with improved cycle life.",
        "doc_type": "patent",
        "publication_date": "2021-11-20",
        "citation_count": 8,
        "tags": json.dumps(["solid-state", "electrodes"]),
        "source_url": "https://example.com/patent/002",
    },
    {
        "doc_id": "mtest_paper_002",
        "title": "Machine learning for drug discovery",
        "abstract": "A comprehensive survey of machine learning techniques applied to drug discovery, covering molecular representation learning, virtual screening, de novo drug design, and ADMET property prediction.",
        "doc_type": "paper",
        "publication_date": "2023-01-10",
        "citation_count": 120,
        "tags": json.dumps(["machine learning", "drug discovery"]),
        "source_url": "https://example.com/paper/002",
    },
    {
        "doc_id": "mtest_paper_003",
        "title": "Reinforcement learning for robotic manipulation",
        "abstract": "This work explores the application of model-free reinforcement learning algorithms for dexterous robotic manipulation tasks, demonstrating improved sample efficiency through curriculum learning.",
        "doc_type": "paper",
        "publication_date": "2022-09-05",
        "citation_count": 30,
        "tags": json.dumps(["reinforcement learning", "robotics"]),
        "source_url": "https://example.com/paper/003",
    },
]


@pytest.fixture(scope="module")
def embedding_service():
    return EmbeddingService()


@pytest.fixture(scope="module")
def milvus_client():
    original = settings.collection_name
    settings.collection_name = TEST_COLLECTION
    client = MilvusClient()
    yield client
    from pymilvus import utility
    if utility.has_collection(TEST_COLLECTION):
        utility.drop_collection(TEST_COLLECTION)
    settings.collection_name = original
    client.close()


@pytest.fixture(scope="module")
def metadata_store():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    store = MetadataStore(tmp.name)
    yield store
    store.close()
    os.unlink(tmp.name)


@pytest.fixture(scope="module")
def seeded_data(embedding_service, milvus_client, metadata_store):
    abstracts = [d["abstract"] for d in SAMPLE_DOCS]
    embeddings = embedding_service.encode(abstracts)

    doc_ids = [d["doc_id"] for d in SAMPLE_DOCS]
    doc_types = [d["doc_type"] for d in SAMPLE_DOCS]

    count = milvus_client.insert(doc_ids, doc_types, embeddings.tolist())
    metadata_store.insert_batch(SAMPLE_DOCS)
    print(f"\nSeeded {count} documents into Milvus collection '{TEST_COLLECTION}'")
    time.sleep(1)
    return True


class TestMilvusEndToEnd:
    def test_milvus_connection(self, milvus_client):
        assert milvus_client.collection is not None
        print(f"\nCollection: {milvus_client.collection.name}")

    def test_insert_and_search(self, seeded_data, embedding_service, milvus_client):
        query = "lithium battery thermal management"
        query_vec = embedding_service.encode_query(query).tolist()
        results = milvus_client.search(query_vec, top_k=5)

        assert len(results) > 0
        print(f"\n--- Milvus search results for '{query}' ---")
        for r in results:
            print(f"  [{r['score']:.4f}] {r['doc_id']} ({r['doc_type']})")

        assert results[0]["doc_id"] == "mtest_patent_001", \
            f"Expected thermal management patent as top hit, got {results[0]['doc_id']}"

    def test_doc_type_filter(self, seeded_data, embedding_service, milvus_client):
        query_vec = embedding_service.encode_query("machine learning applications").tolist()

        patent_results = milvus_client.search(query_vec, top_k=5, doc_type_filter="patents")
        paper_results = milvus_client.search(query_vec, top_k=5, doc_type_filter="papers")

        for r in patent_results:
            assert r["doc_type"] == "patent", f"Expected patent, got {r['doc_type']}"
        for r in paper_results:
            assert r["doc_type"] == "paper", f"Expected paper, got {r['doc_type']}"

        print(f"\n--- Patents only: {len(patent_results)} results ---")
        print(f"--- Papers only: {len(paper_results)} results ---")

    def test_get_vectors_by_ids(self, seeded_data, milvus_client):
        vectors = milvus_client.get_vectors_by_ids(["mtest_patent_001", "mtest_paper_001"])
        assert len(vectors) == 2
        assert len(vectors["mtest_patent_001"]) == 384
        print(f"\nRetrieved vectors for {len(vectors)} documents")

    def test_full_search_service(self, seeded_data, embedding_service, milvus_client, metadata_store):
        search_service = SearchService(
            embedding_service=embedding_service,
            milvus_client=milvus_client,
            metadata_store=metadata_store,
        )

        response = search_service.search(
            query="lithium battery technology",
            doc_type="both",
            limit=5,
        )

        assert len(response.results) > 0
        assert len(response.clusters) >= 1
        assert response.total_time_ms > 0

        print(f"\n=== Full SearchService Response ===")
        print(f"  Results: {len(response.results)}")
        print(f"  Clusters: {len(response.clusters)}")
        print(f"  Heatmap cells: {len(response.heatmap.cells)}")
        print(f"  Time: {response.total_time_ms:.1f}ms")
        for r in response.results:
            print(f"  [{r.score:.3f}] {r.title} ({r.doc_type}) cluster={r.cluster_id}")

        json_out = response.model_dump_json()
        assert len(json_out) > 100
        print(f"  JSON size: {len(json_out)} bytes")

    def test_search_with_date_filter(self, seeded_data, embedding_service, milvus_client, metadata_store):
        search_service = SearchService(
            embedding_service=embedding_service,
            milvus_client=milvus_client,
            metadata_store=metadata_store,
        )

        response = search_service.search(
            query="battery",
            date_from="2023-01-01",
            limit=5,
        )

        for r in response.results:
            assert r.publication_date >= "2023-01-01", \
                f"Date filter failed: {r.publication_date}"
        print(f"\n--- Date filtered (>=2023): {len(response.results)} results ---")

    def test_search_with_citation_filter(self, seeded_data, embedding_service, milvus_client, metadata_store):
        search_service = SearchService(
            embedding_service=embedding_service,
            milvus_client=milvus_client,
            metadata_store=metadata_store,
        )

        response = search_service.search(
            query="machine learning",
            min_citations=30,
            limit=5,
        )

        for r in response.results:
            assert r.citation_count >= 30, \
                f"Citation filter failed: {r.citation_count}"
        print(f"\n--- Citation filtered (>=30): {len(response.results)} results ---")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
