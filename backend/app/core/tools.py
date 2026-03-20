import json
from typing import Literal
import httpx
from langchain_core.tools import StructuredTool
from pydantic import BaseModel

from app.config import settings


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


# --- Async executor functions ---

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
        name="crud_data",
        description=(
            "Create, read, update, or delete data in an external system. "
            "Action must be one of: create, read, update, delete."
        ),
        args_schema=CRUDDataInput,
        coroutine=crud_data_executor,
    ),
]
