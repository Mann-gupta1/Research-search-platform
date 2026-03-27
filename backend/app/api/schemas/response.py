from typing import Optional

from pydantic import BaseModel


class DocumentResult(BaseModel):
    doc_id: str
    title: str
    abstract: str
    doc_type: str
    publication_date: Optional[str] = None
    citation_count: Optional[int] = None
    tags: list[str] = []
    score: float
    cluster_id: Optional[int] = None


class SubTopic(BaseModel):
    cluster_id: int
    label: str
    keywords: list[str]
    doc_count: int


class HeatmapCell(BaseModel):
    sub_topic: str
    year: int
    count: int


class HeatmapData(BaseModel):
    cells: list[HeatmapCell]
    sub_topics: list[str]
    years: list[int]
    velocities: dict[str, float]


class SearchResponse(BaseModel):
    results: list[DocumentResult]
    clusters: list[SubTopic]
    heatmap: HeatmapData
    total_time_ms: float
