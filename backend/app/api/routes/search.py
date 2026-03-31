from fastapi import APIRouter, Request

from app.api.schemas.request import SearchRequest
from app.api.schemas.response import SearchResponse
from app.services.search import SearchService

router = APIRouter()


@router.get("/search")
async def search_get_help():
    return {
        "message": "Use HTTP POST with Content-Type: application/json",
        "method": "POST",
        "url": "/api/search",
        "body_example": {
            "query": "lithium ion battery thermal management",
            "doc_type": "both",
            "limit": 10,
        },
    }


@router.post("/search", response_model=SearchResponse)
async def search_documents(request: Request, body: SearchRequest):
    search_service = SearchService(
        embedding_service=request.app.state.embedding_service,
        milvus_client=request.app.state.milvus_client,
        metadata_store=request.app.state.metadata_store,
    )

    response = search_service.search(
        query=body.query,
        doc_type=body.doc_type,
        date_from=str(body.date_from) if body.date_from else None,
        date_to=str(body.date_to) if body.date_to else None,
        min_citations=body.min_citations,
        tags=body.tags,
        limit=body.limit,
    )

    return response
