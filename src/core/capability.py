from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class Capability(ABC):
    """
    Base class for all capabilities (Code Agents, Tools, MCP Tools).
    """
    name: str
    description: str
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    def to_function_schema(self) -> Dict[str, Any]:
        """
        Returns the OpenAI function schema for this capability.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    @abstractmethod
    async def execute(self, **kwargs) -> str:
        """
        Execute the capability.
        """
        pass

class BaseTool(Capability):
    """
    Represents a pure python function tool.
    """
    pass

class BaseAgent(Capability):
    """
    Represents a Code Agent (Agentic Tool) that uses LLM internally.
    """
    system_prompt: str = ""
    allowed_tools: List[str] = [] # List of tool names this agent can use
    
    # Default parameters for all Agents (they all take 'instruction')
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "The natural language instruction for this agent."
            },
            "context": {
                "type": "string",
                "description": "Optional background context provided by the system/compressor."
            }
        },
        "required": ["instruction"]
    }

    def get_allowed_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        Retrieve schemas for tools that this agent is allowed to use.
        """
        from src.core.registry import global_registry
        return global_registry.get_all_tool_schemas(whitelist=self.allowed_tools)


    async def execute(self, instruction: str, context: Optional[str] = None) -> str:
        """
        Default execution for an agent: takes an instruction and processes it.
        Subclasses can override this to implement specific logic.
        """
        # This is a placeholder. Real implementation will use the injected context.
        # For debug, we can print what we received if not overridden
        if context:
            print(f"[{self.name}] Received Context: {len(context)} chars")
        
        raise NotImplementedError("Agent execution logic must be implemented")
