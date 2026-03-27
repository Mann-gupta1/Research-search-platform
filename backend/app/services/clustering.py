import logging
from collections import Counter

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


class ClusteringService:
    def __init__(self, n_clusters: int = 5):
        self.n_clusters = n_clusters

    def cluster_documents(
        self,
        embeddings: np.ndarray,
        abstracts: list[str],
        n_clusters: int | None = None,
    ) -> list[dict]:
        """
        Cluster documents by their embeddings and extract keyword labels.

        Returns a list of cluster info dicts:
            {cluster_id, label, keywords, doc_indices}
        """
        k = n_clusters or self.n_clusters
        n_docs = len(abstracts)

        if n_docs < k:
            k = max(1, n_docs)

        if n_docs <= 1:
            return [
                {
                    "cluster_id": 0,
                    "label": "All Results",
                    "keywords": [],
                    "doc_indices": list(range(n_docs)),
                }
            ]

        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        clusters = []
        for cid in range(k):
            indices = [i for i, lbl in enumerate(labels) if lbl == cid]
            if not indices:
                continue

            cluster_abstracts = [abstracts[i] for i in indices]
            keywords = self._extract_keywords(cluster_abstracts)
            label = " / ".join(keywords[:3]) if keywords else f"Cluster {cid}"

            clusters.append(
                {
                    "cluster_id": cid,
                    "label": label,
                    "keywords": keywords,
                    "doc_indices": indices,
                }
            )

        return clusters

    def _extract_keywords(
        self, texts: list[str], top_n: int = 5
    ) -> list[str]:
        if not texts:
            return []

        try:
            vectorizer = TfidfVectorizer(
                max_features=100,
                stop_words="english",
                max_df=0.95,
                min_df=1,
                ngram_range=(1, 2),
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
            feature_names = vectorizer.get_feature_names_out()

            mean_tfidf = np.array(tfidf_matrix.mean(axis=0)).flatten()
            top_indices = mean_tfidf.argsort()[-top_n:][::-1]
            return [feature_names[i] for i in top_indices]
        except Exception as e:
            logger.warning("Keyword extraction failed: %s", e)
            return []

    def assign_labels(
        self, embeddings: np.ndarray, abstracts: list[str]
    ) -> tuple[list[int], list[dict]]:
        """Returns (cluster_labels_per_doc, cluster_info_list)."""
        cluster_info = self.cluster_documents(embeddings, abstracts)

        labels = [0] * len(abstracts)
        for ci in cluster_info:
            for idx in ci["doc_indices"]:
                labels[idx] = ci["cluster_id"]

        return labels, cluster_info
