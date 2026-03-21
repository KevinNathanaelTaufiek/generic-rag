import asyncio
from pydantic import BaseModel
from langchain_core.tools import StructuredTool

from app.core.tools.base import BaseTool


class SearchWebInput(BaseModel):
    query: str


class SearchWebTool(BaseTool):
    """Search the web using Tavily Search API."""

    _MAX_RESULTS: int = 5

    @property
    def name(self) -> str:
        return "search_web"

    @property
    def description(self) -> str:
        return (
            "Search the web for information about a topic or recent events. "
            "Use when the user asks about something not in the knowledge base."
        )

    async def _execute(self, query: str) -> str:
        try:
            results = await asyncio.get_event_loop().run_in_executor(
                None, self._tavily_search, query
            )
            if not results:
                return "No results found for the given query."
            lines = [
                f"- {r['title']}: {r['content']} ({r['url']})"
                for r in results
            ]
            return "\n".join(lines)
        except Exception as e:
            return f"Error: Web search failed — {str(e)}"

    def _tavily_search(self, query: str) -> list[dict]:
        from tavily import TavilyClient
        from app.config import settings
        client = TavilyClient(api_key=settings.tavily_api_key)
        response = client.search(query, max_results=self._MAX_RESULTS)
        return response.get("results", [])

    def build(self) -> StructuredTool:
        return StructuredTool(
            name=self.name,
            description=self.description,
            args_schema=SearchWebInput,
            coroutine=self._execute,
        )
