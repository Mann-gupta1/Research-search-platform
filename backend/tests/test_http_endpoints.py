"""
HTTP endpoint test against a running FastAPI server.
Requires: uvicorn app.main:app running on localhost:8000 with Milvus
"""

import json
import requests
import sys


def test_health():
    print("=== GET /api/health ===")
    r = requests.get("http://localhost:8000/api/health", timeout=10)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    print(f"  Status: {r.status_code} -> {data}")


def test_search_basic():
    print("\n=== POST /api/search (basic) ===")
    payload = {
        "query": "lithium battery thermal management",
        "doc_type": "both",
        "limit": 10,
    }
    r = requests.post("http://localhost:8000/api/search", json=payload, timeout=60)
    assert r.status_code == 200
    data = r.json()

    n_results = len(data["results"])
    n_clusters = len(data["clusters"])
    n_cells = len(data["heatmap"]["cells"])
    elapsed = data["total_time_ms"]

    print(f"  Results: {n_results} documents")
    print(f"  Clusters: {n_clusters} sub-topics")
    print(f"  Heatmap: {n_cells} cells")
    print(f"  Time: {elapsed:.1f}ms")

    assert "results" in data
    assert "clusters" in data
    assert "heatmap" in data
    assert "total_time_ms" in data

    if n_results > 0:
        print("  Top results:")
        for res in data["results"][:3]:
            print(f"    [{res['score']:.3f}] {res['title']} ({res['doc_type']})")

    if n_clusters > 0:
        print("  Clusters:")
        for c in data["clusters"]:
            print(f"    {c['label']} ({c['doc_count']} docs)")

    if data["heatmap"]["velocities"]:
        print(f"  Velocities: {data['heatmap']['velocities']}")


def test_search_with_filters():
    print("\n=== POST /api/search (with filters) ===")
    payload = {
        "query": "machine learning",
        "doc_type": "papers",
        "min_citations": 20,
        "limit": 5,
    }
    r = requests.post("http://localhost:8000/api/search", json=payload, timeout=60)
    assert r.status_code == 200
    data = r.json()

    print(f"  Results: {len(data['results'])} (papers only, >=20 citations)")
    for res in data["results"]:
        assert res["doc_type"] == "paper", f"Expected paper, got {res['doc_type']}"
        print(f"    [{res['score']:.3f}] {res['title']} (citations: {res['citation_count']})")


def test_search_empty_query():
    print("\n=== POST /api/search (validation) ===")
    payload = {"query": "", "limit": 10}
    r = requests.post("http://localhost:8000/api/search", json=payload, timeout=10)
    assert r.status_code == 422, f"Expected 422 for empty query, got {r.status_code}"
    print(f"  Empty query correctly rejected: {r.status_code}")


def test_openapi_docs():
    print("\n=== GET /docs ===")
    r = requests.get("http://localhost:8000/docs", timeout=10)
    assert r.status_code == 200
    print(f"  OpenAPI docs accessible: {r.status_code}")


if __name__ == "__main__":
    tests = [test_health, test_search_basic, test_search_with_filters, test_search_empty_query, test_openapi_docs]
    passed = 0
    failed = 0

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
            print(f"  -> PASSED")
        except Exception as e:
            failed += 1
            print(f"  -> FAILED: {e}")

    print(f"\n{'='*50}")
    print(f"HTTP Endpoint Tests: {passed} passed, {failed} failed")
    if failed > 0:
        sys.exit(1)
    print("All HTTP endpoint tests PASSED!")
