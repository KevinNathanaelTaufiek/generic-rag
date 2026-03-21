import json
from typing import Literal
import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.config import settings
from app.core.vectorstore import get_vectorstore


# --- Input schemas ---

class SearchWebInput(BaseModel):
    query: str


class SendNotificationInput(BaseModel):
    to: str
    message: str


class CRUDDataInput(BaseModel):
    action: Literal["create", "read", "update", "delete"]
    resource: str
    data: dict = {}


class GetRandomNumberInput(BaseModel):
    min: int = 1
    max: int = 100


class SearchKnowledgeInput(BaseModel):
    query: str


# --- Async executor functions ---

async def search_knowledge_executor(query: str) -> str:
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


async def search_web_executor(query: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/search",
                json={"query": query},
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if not results:
                return "No results found."
            lines = [f"- {r['title']}: {r['snippet']} ({r['url']})" for r in results]
            return "\n".join(lines)
    except httpx.TimeoutException:
        return "Error: Search service timed out. Please try again."
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return f"Error: Search service unavailable (HTTP {e.response.status_code})."
        return f"Error: Invalid search request (HTTP {e.response.status_code})."
    except Exception as e:
        return f"Error: Search failed — {str(e)}"


async def send_notification_executor(to: str, message: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/notify",
                json={"to": to, "message": message},
            )
            resp.raise_for_status()
            data = resp.json()
            return f"Notification sent to '{data['to']}' at {data['timestamp']}."
    except httpx.TimeoutException:
        return "Error: Notification service timed out."
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return f"Error: Notification service unavailable (HTTP {e.response.status_code})."
        return f"Error: Invalid notification request (HTTP {e.response.status_code})."
    except Exception as e:
        return f"Error: Notification failed — {str(e)}"


async def get_random_number_executor(min: int = 1, max: int = 100) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/random-number",
                json={"min": min, "max": max},
            )
            resp.raise_for_status()
            data = resp.json()
            return f"Random number between {data['min']} and {data['max']}: {data['number']}"
    except httpx.TimeoutException:
        return "Error: Random number service timed out."
    except httpx.HTTPStatusError as e:
        return f"Error: Random number service returned HTTP {e.response.status_code}."
    except Exception as e:
        return f"Error: Failed to get random number — {str(e)}"


async def crud_data_executor(action: str, resource: str, data: dict) -> str:
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{settings.dummy_services_base_url}/data",
                json={"action": action, "resource": resource, "data": data},
            )
            resp.raise_for_status()
            result = resp.json()
            return f"Action '{action}' on '{resource}': success={result['success']}, data={json.dumps(result['data'])}"
    except httpx.TimeoutException:
        return "Error: Data service timed out."
    except httpx.HTTPStatusError as e:
        if e.response.status_code >= 500:
            return f"Error: Data service unavailable (HTTP {e.response.status_code})."
        return f"Error: Invalid data request (HTTP {e.response.status_code})."
    except Exception as e:
        return f"Error: Data operation failed — {str(e)}"


# --- Tool registry ---
# Use coroutine= (not func=) for async tools in StructuredTool.
# Invoke via: await tool.ainvoke({"param": value})

TOOL_NAMES: list[str] = ["search_web", "send_notification", "get_random_number", "crud_data"]

SEARCH_KNOWLEDGE_TOOL = StructuredTool(
    name="search_knowledge",
    description=(
        "Search the internal knowledge base for information that has been added by the user. "
        "Always use this tool FIRST before any other tool when answering questions. "
        "Returns relevant excerpts from stored documents."
    ),
    args_schema=SearchKnowledgeInput,
    coroutine=search_knowledge_executor,
)


def get_tools(enabled: list[str] | None = None) -> list[StructuredTool]:
    """
    Return tools based on enabled list sent by frontend.

    Frontend sends the exact list of toggled-on tools (including/excluding "search_knowledge").
    - None → not specified → default: knowledge only
    - []   → user disabled all → no tools (LLM answers from general knowledge)
    - ["search_knowledge", ...] → knowledge first + other enabled tools
    - ["search_web", ...]       → other tools only, no knowledge
    """
    if enabled is None:
        return [SEARCH_KNOWLEDGE_TOOL]

    result = []
    if "search_knowledge" in enabled:
        result.append(SEARCH_KNOWLEDGE_TOOL)

    other = [t for t in TOOLS if t.name in enabled]
    return result + other


TOOLS: list[StructuredTool] = [
    StructuredTool(
        name="search_web",
        description=(
            "Search the web for information about a topic or recent events. "
            "Use when the user asks about something not in the knowledge base."
        ),
        args_schema=SearchWebInput,
        coroutine=search_web_executor,
    ),
    StructuredTool(
        name="send_notification",
        description="Send a notification or message to a recipient.",
        args_schema=SendNotificationInput,
        coroutine=send_notification_executor,
    ),
    StructuredTool(
        name="get_random_number",
        description=(
            "Generate a random number between min and max (inclusive). "
            "Default range is 1 to 100."
        ),
        args_schema=GetRandomNumberInput,
        coroutine=get_random_number_executor,
    ),
    StructuredTool(
        name="crud_data",
        description=(
            "Create, read, update, or delete data in an external system. "
            "Action must be one of: create, read, update, delete."
        ),
        args_schema=CRUDDataInput,
        coroutine=crud_data_executor,
    ),
]
