from pydantic import BaseModel
from langchain_core.tools import StructuredTool

from app.config import settings
from app.core.vectorstore import get_vectorstore
from app.core.tools.base import BaseTool


class SearchKnowledgeInput(BaseModel):
    query: str


class SearchKnowledgeTool(BaseTool):
    """Search the internal ChromaDB knowledge base."""

    @property
    def name(self) -> str:
        return "search_knowledge"

    @property
    def description(self) -> str:
        return (
            "Search the internal knowledge base for information that has been added by the user. "
            "Always use this tool FIRST before any other tool when answering questions. "
            "Returns relevant excerpts from stored documents."
        )

    async def _execute(self, query: str) -> str:
        try:
            vectorstore = get_vectorstore()
            results = vectorstore.similarity_search_with_relevance_scores(query, k=settings.top_k_results)
            relevant = [(doc, score) for doc, score in results if score >= 0.5]
            if not relevant:
                return "No relevant information found in the knowledge base."
            parts = []
            for doc, score in relevant:
                meta = doc.metadata
                title = meta.get("title", "Unknown")
                doc_id = meta.get("doc_id", "")
                parts.append(f"[source: {title} | doc_id: {doc_id} | score: {score:.2f}]\n{doc.page_content}")
            return "\n\n---\n\n".join(parts)
        except Exception as e:
            return f"Error: Knowledge base search failed — {str(e)}"

    def build(self) -> StructuredTool:
        return StructuredTool(
            name=self.name,
            description=self.description,
            args_schema=SearchKnowledgeInput,
            coroutine=self._execute,
        )
