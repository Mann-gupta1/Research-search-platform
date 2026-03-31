from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator


class SearchRequest(BaseModel):
    query: str = Field(
        default="",
        max_length=10000,
        description="Natural language search query (omit or empty when browse=true)",
    )
    browse: bool = Field(
        default=False,
        description="If true, return recent documents from the index without semantic search",
    )
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

    @model_validator(mode="after")
    def query_required_unless_browse(self):
        if not self.browse and not (self.query and self.query.strip()):
            raise ValueError("query must not be empty unless browse is true")
        return self
