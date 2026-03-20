from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class SearchRequest(BaseModel):
    query: str


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str


class SearchResponse(BaseModel):
    results: list[SearchResult]


@router.post("/search", response_model=SearchResponse)
def search(body: SearchRequest):
    return SearchResponse(results=[
        SearchResult(
            title=f"Result 1 for: {body.query}",
            snippet=f"This is a fake snippet about '{body.query}'. Lorem ipsum dolor sit amet.",
            url="https://example.com/result-1",
        ),
        SearchResult(
            title=f"Result 2 for: {body.query}",
            snippet=f"Another fake result related to '{body.query}'. Consectetur adipiscing elit.",
            url="https://example.com/result-2",
        ),
        SearchResult(
            title=f"Result 3 for: {body.query}",
            snippet=f"Third fake result about '{body.query}'. Sed do eiusmod tempor incididunt.",
            url="https://example.com/result-3",
        ),
    ])
