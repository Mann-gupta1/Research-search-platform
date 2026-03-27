from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    doc_type: Literal["patents", "papers", "both"] = Field(
        default="both", description="Filter by document type"
    )
    date_from: Optional[date] = Field(
        default=None, description="Start of publication date range"
    )
    date_to: Optional[date] = Field(
        default=None, description="End of publication date range"
    )
    min_citations: Optional[int] = Field(
        default=None, ge=0, description="Minimum citation count filter"
    )
    tags: Optional[list[str]] = Field(
        default=None,
        description="Filter by field-of-research or classification tags (any match)",
    )
    limit: int = Field(default=50, ge=1, le=100, description="Max results to return")
