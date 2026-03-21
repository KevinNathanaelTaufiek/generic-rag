"""
Tool registry — exports TOOLS, TOOL_NAMES, SEARCH_KNOWLEDGE_TOOL, get_tools.

Static tools  : search_knowledge, search_web (defined as classes in this package)
Dynamic tools : loaded from microservices.json via MicroserviceTool (generic HTTP caller)

To add a new microservice tool: add an entry to backend/microservices.json.
To add a new first-class tool  : create a file, subclass BaseTool, register below.
"""
import json
import logging
import jsonschema
from pathlib import Path
from langchain_core.tools import StructuredTool

from app.core.tools.search_knowledge import SearchKnowledgeTool
from app.core.tools.search_web import SearchWebTool
from app.core.tools.microservice import MicroserviceTool

logger = logging.getLogger(__name__)

# Path to microservices config — relative to this package, two levels up to backend/
_MICROSERVICES_JSON = Path(__file__).parent.parent.parent.parent / "microservices.json"

# Meta-schema: validates the structure of each entry in microservices.json
_ENTRY_META_SCHEMA = {
    "type": "object",
    "required": ["name", "description", "endpoint", "method", "args_schema", "response_schema", "args_example", "response_example"],
    "properties": {
        "name":             {"type": "string", "minLength": 1},
        "description":      {"type": "string", "minLength": 1},
        "endpoint":         {"type": "string", "pattern": "^https?://"},
        "method":           {"type": "string", "enum": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
        "args_schema":      {"type": "object", "required": ["type", "properties"]},
        "response_schema":  {"type": "object", "required": ["type", "properties"]},
        "args_example":     {"type": "object"},
        "response_example": {"type": "object"},
    },
    "additionalProperties": False,
}


def _validate_microservices_json(configs: list[dict]) -> None:
    """
    Validate every entry in microservices.json. Raises ValueError on first failure.
    Checks:
    1. Entry structure matches meta-schema
    2. args_example is valid against args_schema
    3. response_example is valid against response_schema
    """
    for i, config in enumerate(configs):
        name = config.get("name", f"entry[{i}]")
        try:
            jsonschema.validate(config, _ENTRY_META_SCHEMA)
        except jsonschema.ValidationError as e:
            raise ValueError(f"[microservices.json] '{name}' has invalid structure: {e.message}") from e

        try:
            jsonschema.validate(config["args_example"], config["args_schema"])
        except jsonschema.ValidationError as e:
            raise ValueError(f"[microservices.json] '{name}' args_example does not match args_schema: {e.message}") from e

        try:
            jsonschema.validate(config["response_example"], config["response_schema"])
        except jsonschema.ValidationError as e:
            raise ValueError(f"[microservices.json] '{name}' response_example does not match response_schema: {e.message}") from e

        logger.info("[tools] validated microservice config: %s", name)


def _load_microservice_tools() -> list[StructuredTool]:
    if not _MICROSERVICES_JSON.exists():
        logger.warning("[tools] microservices.json not found at %s — no microservice tools loaded", _MICROSERVICES_JSON)
        return []
    with open(_MICROSERVICES_JSON, encoding="utf-8") as f:
        configs = json.load(f)

    # Fail fast — raises ValueError if any entry is invalid
    _validate_microservices_json(configs)

    tools = []
    for config in configs:
        tools.append(MicroserviceTool(config).build())
        logger.info("[tools] loaded microservice tool: %s", config["name"])
    return tools


# Build singleton instances
SEARCH_KNOWLEDGE_TOOL: StructuredTool = SearchKnowledgeTool().build()
_search_web_tool: StructuredTool = SearchWebTool().build()
_microservice_tools: list[StructuredTool] = _load_microservice_tools()

# Public constants — same interface as the old tools.py
TOOLS: list[StructuredTool] = [_search_web_tool] + _microservice_tools
TOOL_NAMES: list[str] = [t.name for t in TOOLS]


def get_tools(enabled: list[str] | None = None) -> list[StructuredTool]:
    """
    Return tools based on enabled list sent by frontend.

    - None → not specified → default: knowledge only
    - []   → user disabled all → no tools
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
