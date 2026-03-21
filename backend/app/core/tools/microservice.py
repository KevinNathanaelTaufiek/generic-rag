"""
Generic microservice tool — one class handles any HTTP microservice defined in microservices.json.

Responsibilities:
- Build a dynamic Pydantic args schema from JSON Schema (args_schema)
- Route each argument to path / query / body based on x-param-style
- Call the endpoint via httpx
- Validate the response against response_schema (jsonschema)
- On validation failure: return error message + raw response
- Inject args_example into LLM description when schema is complex (nested/array fields present)
"""
import json
import logging
import asyncio
import httpx
import jsonschema
from typing import Any
from pydantic import BaseModel, create_model
from langchain_core.tools import StructuredTool

from app.core.tools.base import BaseTool

logger = logging.getLogger(__name__)

# JSON Schema type → Python type mapping
_TYPE_MAP: dict[str, type] = {
    "string":  str,
    "integer": int,
    "number":  float,
    "boolean": bool,
    "object":  dict,
    "array":   list,
}


def _json_schema_to_pydantic(schema: dict) -> type[BaseModel]:
    """
    Dynamically build a Pydantic BaseModel from a JSON Schema object.
    Supports: string, integer, number, boolean, object, array, enum (as str with validation).
    Optional fields (not in 'required') get a default of None.
    Fields with a 'default' value use that default.
    """
    properties: dict = schema.get("properties", {})
    required: list[str] = schema.get("required", [])
    fields: dict[str, Any] = {}

    for field_name, field_def in properties.items():
        raw_type = field_def.get("type", "string")
        python_type = _TYPE_MAP.get(raw_type, str)
        has_default = "default" in field_def
        is_required = field_name in required

        if is_required:
            fields[field_name] = (python_type, ...)
        elif has_default:
            fields[field_name] = (python_type, field_def["default"])
        else:
            fields[field_name] = (python_type | None, None)

    return create_model("DynamicArgs", **fields)


def _is_complex_schema(args_schema: dict) -> bool:
    """Return True if any property is array or object type — hint to inject args_example."""
    for prop in args_schema.get("properties", {}).values():
        if prop.get("type") in ("array", "object"):
            return True
    return False


def _build_description(base_description: str, args_schema: dict, args_example: dict) -> str:
    """Append args_example to description only when schema is complex."""
    if not _is_complex_schema(args_schema):
        return base_description
    example_str = json.dumps(args_example, indent=2)
    return f"{base_description}\n\nExample args:\n{example_str}"


def _build_body_args(args_schema: dict, kwargs: dict) -> dict:
    """Extract only 'body' args (x-param-style == 'body' or missing) from kwargs."""
    body = {}
    for field_name, field_def in args_schema.get("properties", {}).items():
        style = field_def.get("x-param-style", "body")
        if style == "body" and field_name in kwargs and kwargs[field_name] is not None:
            body[field_name] = kwargs[field_name]
    return body


def _build_path_and_query(args_schema: dict, endpoint: str, kwargs: dict) -> tuple[str, dict]:
    """Substitute path variables and collect query params from kwargs."""
    query_params = {}
    url = endpoint
    for field_name, field_def in args_schema.get("properties", {}).items():
        style = field_def.get("x-param-style", "body")
        value = kwargs.get(field_name)
        if value is None:
            continue
        if style == "path":
            url = url.replace(f"{{{field_name}}}", str(value))
        elif style == "query":
            query_params[field_name] = value
    return url, query_params


class MicroserviceTool(BaseTool):
    """
    Generic tool that calls an HTTP microservice endpoint.
    Configured entirely from a single microservices.json entry.
    """

    def __init__(self, config: dict) -> None:
        self._config = config
        self._args_model = _json_schema_to_pydantic(config["args_schema"])

    @property
    def name(self) -> str:
        return self._config["name"]

    @property
    def description(self) -> str:
        return _build_description(
            self._config["description"],
            self._config["args_schema"],
            self._config.get("args_example", {}),
        )

    async def _execute(self, **kwargs) -> str:
        config = self._config
        endpoint = config["endpoint"]
        method = config["method"].upper()
        args_schema = config["args_schema"]
        response_schema = config["response_schema"]

        url, query_params = _build_path_and_query(args_schema, endpoint, kwargs)
        body = _build_body_args(args_schema, kwargs)

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.request(
                    method=method,
                    url=url,
                    params=query_params if query_params else None,
                    json=body if body else None,
                )
                resp.raise_for_status()
                raw = resp.json()
        except httpx.TimeoutException:
            return f"Error: {self.name} service timed out."
        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            if status >= 500:
                return f"Error: {self.name} service unavailable (HTTP {status})."
            return f"Error: Invalid request to {self.name} (HTTP {status})."
        except Exception as e:
            return f"Error: {self.name} call failed — {str(e)}"

        # Validate response against response_schema
        try:
            jsonschema.validate(raw, response_schema)
        except jsonschema.ValidationError as e:
            raw_str = json.dumps(raw)
            logger.warning("[microservice] %s response validation failed: %s", self.name, e.message)
            return (
                f"Error: {self.name} returned an unexpected response format — {e.message}. "
                f"Raw response: {raw_str}"
            )

        return json.dumps(raw)

    def build(self) -> StructuredTool:
        # Capture self for use inside the coroutine closure
        tool = self

        async def _coroutine(**kwargs) -> str:
            return await tool._execute(**kwargs)

        return StructuredTool(
            name=self.name,
            description=self.description,
            args_schema=self._args_model,
            coroutine=_coroutine,
        )
