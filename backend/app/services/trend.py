import logging
from collections import defaultdict

import numpy as np

logger = logging.getLogger(__name__)


class TrendService:
    def compute_trends(
        self,
        cluster_labels: list[int],
        cluster_info: list[dict],
        publication_dates: list[str],
    ) -> dict:
        """
        Build a heatmap matrix (sub-topic x year) and compute velocity per sub-topic.

        Returns:
            {
                "cells": [{"sub_topic": str, "year": int, "count": int}, ...],
                "sub_topics": [str, ...],
                "years": [int, ...],
                "velocities": {"sub_topic_label": slope, ...}
            }
        """
        cluster_label_map = {ci["cluster_id"]: ci["label"] for ci in cluster_info}

        groups = defaultdict(lambda: defaultdict(int))
        for label, date_str in zip(cluster_labels, publication_dates):
            year = self._extract_year(date_str)
            if year is None:
                continue
            topic_label = cluster_label_map.get(label, f"Cluster {label}")
            groups[topic_label][year] += 1

        if not groups:
            return {
                "cells": [],
                "sub_topics": [],
                "years": [],
                "velocities": {},
            }

        all_years = set()
        for year_counts in groups.values():
            all_years.update(year_counts.keys())
        years_sorted = sorted(all_years)
        sub_topics = sorted(groups.keys())

        cells = []
        for topic in sub_topics:
            for year in years_sorted:
                count = groups[topic].get(year, 0)
                cells.append({
                    "sub_topic": topic,
                    "year": year,
                    "count": count,
                })

        velocities = {}
        for topic in sub_topics:
            velocities[topic] = self._compute_velocity(
                groups[topic], years_sorted
            )

        return {
            "cells": cells,
            "sub_topics": sub_topics,
            "years": years_sorted,
            "velocities": velocities,
        }

    def _extract_year(self, date_str: str) -> int | None:
        if not date_str:
            return None
        try:
            return int(date_str[:4])
        except (ValueError, IndexError):
            return None

    def _compute_velocity(
        self, year_counts: dict[int, int], years: list[int]
    ) -> float:
        """Linear regression slope of counts over years."""
        if len(years) < 2:
            return 0.0

        x = np.array([float(y) for y in years])
        y_vals = np.array([float(year_counts.get(yr, 0)) for yr in years])

        if y_vals.sum() == 0:
            return 0.0

        x_mean = x.mean()
        y_mean = y_vals.mean()
        numerator = ((x - x_mean) * (y_vals - y_mean)).sum()
        denominator = ((x - x_mean) ** 2).sum()

        if denominator == 0:
            return 0.0

        slope = float(numerator / denominator)
        return round(slope, 4)
