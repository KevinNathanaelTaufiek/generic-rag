from abc import ABC, abstractmethod
from langchain_core.tools import StructuredTool


class BaseTool(ABC):
    """Abstract base class for all agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool identifier used by the LLM."""

    @property
    @abstractmethod
    def description(self) -> str:
        """Human/LLM-readable description of what the tool does."""

    @abstractmethod
    def build(self) -> StructuredTool:
        """Return a LangChain StructuredTool instance."""
