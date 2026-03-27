"""
One-time data seeding script.
Run after Docker containers are up to ingest patents and papers into Milvus + SQLite.

Usage:
    python scripts/seed_data.py [--patents-only | --papers-only]
"""

import argparse
import logging
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Seed data into the search platform")
    parser.add_argument("--patents-only", action="store_true", help="Only ingest patents")
    parser.add_argument("--papers-only", action="store_true", help="Only ingest papers")
    args = parser.parse_args()

    if not args.papers_only:
        logger.info("=== Starting patent ingestion ===")
        from app.ingestion.ingest_patents import ingest_patents
        ingest_patents()

    if not args.patents_only:
        logger.info("=== Starting research paper ingestion ===")
        from app.ingestion.ingest_papers import ingest_papers
        ingest_papers()

    logger.info("=== Data seeding complete ===")


if __name__ == "__main__":
    main()
