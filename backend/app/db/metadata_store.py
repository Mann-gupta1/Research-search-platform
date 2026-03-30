import logging
import os
import sqlite3
from typing import Optional
import psycopg2
import psycopg2.extras

logger = logging.getLogger(__name__)


class MetadataStore:
    def __init__(self, db_path: str, database_url: Optional[str] = None):
        self.is_postgres = bool(database_url)
        if self.is_postgres:
            self.conn = psycopg2.connect(database_url)
            self._create_tables_postgres()
            logger.info("MetadataStore initialized with PostgreSQL")
        else:
            os.makedirs(
                os.path.dirname(db_path) if os.path.dirname(db_path) else ".",
                exist_ok=True,
            )
            self.conn = sqlite3.connect(db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._create_tables_sqlite()
            logger.info("MetadataStore initialized at %s", db_path)

    def _create_tables_sqlite(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                doc_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                abstract TEXT NOT NULL,
                doc_type TEXT NOT NULL,
                publication_date TEXT,
                citation_count INTEGER DEFAULT 0,
                tags TEXT DEFAULT '[]',
                source_url TEXT
            )
        """)
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type)"
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pub_date ON documents(publication_date)"
        )
        self.conn.commit()

    def _create_tables_postgres(self):
        with self.conn.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    abstract TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    publication_date TEXT,
                    citation_count INTEGER DEFAULT 0,
                    tags TEXT DEFAULT '[]',
                    source_url TEXT
                )
                """
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_doc_type ON documents(doc_type)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_pub_date ON documents(publication_date)"
            )
        self.conn.commit()

    def insert_batch(self, docs: list[dict]):
        if not docs:
            return
        if self.is_postgres:
            with self.conn.cursor() as cursor:
                psycopg2.extras.execute_batch(
                    cursor,
                    """
                    INSERT INTO documents
                    (doc_id, title, abstract, doc_type, publication_date, citation_count, tags, source_url)
                    VALUES (%(doc_id)s, %(title)s, %(abstract)s, %(doc_type)s, %(publication_date)s, %(citation_count)s, %(tags)s, %(source_url)s)
                    ON CONFLICT (doc_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        abstract = EXCLUDED.abstract,
                        doc_type = EXCLUDED.doc_type,
                        publication_date = EXCLUDED.publication_date,
                        citation_count = EXCLUDED.citation_count,
                        tags = EXCLUDED.tags,
                        source_url = EXCLUDED.source_url
                    """,
                    docs,
                )
        else:
            self.conn.executemany(
                """
                INSERT OR REPLACE INTO documents
                (doc_id, title, abstract, doc_type, publication_date, citation_count, tags, source_url)
                VALUES (:doc_id, :title, :abstract, :doc_type, :publication_date, :citation_count, :tags, :source_url)
                """,
                docs,
            )
        self.conn.commit()

    def get_by_ids(self, doc_ids: list[str]) -> list[dict]:
        if not doc_ids:
            return []
        if self.is_postgres:
            placeholders = ",".join("%s" for _ in doc_ids)
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    f"SELECT * FROM documents WHERE doc_id IN ({placeholders})", doc_ids
                )
                return [dict(row) for row in cursor.fetchall()]
        placeholders = ",".join("?" for _ in doc_ids)
        cursor = self.conn.execute(
            f"SELECT * FROM documents WHERE doc_id IN ({placeholders})", doc_ids
        )
        return [dict(row) for row in cursor.fetchall()]

    def get_filtered(
        self,
        doc_ids: list[str],
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_citations: Optional[int] = None,
        tags: Optional[list[str]] = None,
    ) -> list[dict]:
        if not doc_ids:
            return []

        placeholders = ",".join("%s" if self.is_postgres else "?" for _ in doc_ids)
        query = f"SELECT * FROM documents WHERE doc_id IN ({placeholders})"
        params: list = list(doc_ids)

        if date_from:
            query += " AND publication_date >= %s" if self.is_postgres else " AND publication_date >= ?"
            params.append(date_from)
        if date_to:
            query += " AND publication_date <= %s" if self.is_postgres else " AND publication_date <= ?"
            params.append(date_to)
        if min_citations is not None:
            query += " AND citation_count >= %s" if self.is_postgres else " AND citation_count >= ?"
            params.append(min_citations)
        if tags:
            tag_param = "%s" if self.is_postgres else "?"
            tag_clauses = " OR ".join(f"tags LIKE {tag_param}" for _ in tags)
            query += f" AND ({tag_clauses})"
            params.extend(f"%{tag}%" for tag in tags)

        if self.is_postgres:
            with self.conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
        cursor = self.conn.execute(query, params)
        return [dict(row) for row in cursor.fetchall()]

    def count(self) -> int:
        if self.is_postgres:
            with self.conn.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM documents")
                return cursor.fetchone()[0]
        cursor = self.conn.execute("SELECT COUNT(*) FROM documents")
        return cursor.fetchone()[0]

    def close(self):
        self.conn.close()
        logger.info("MetadataStore connection closed")
