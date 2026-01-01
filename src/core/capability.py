from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field

class Capability(ABC):
    """
    所有能力的基类 (Code Agents, Tools, MCP Tools)。
    Base class for all capabilities (Code Agents, Tools, MCP Tools).
    """
    name: str
    description: str
    parameters: Dict[str, Any] = {"type": "object", "properties": {}}

    def to_function_schema(self) -> Dict[str, Any]:
        """
        返回此能力的 OpenAI 函数模式。
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
        执行能力。
        Execute the capability.
        """
        pass

    def get_context_description(self) -> str:
        """
        获取用于上下文树状图的简短描述。
        Get short description for context tree view.
        """
        return f"{self.name}: {self.description}"

class BaseTool(Capability):
    """
    代表纯 Python 函数工具。
    Represents a pure python function tool.
    """
    pass

class BaseAgent(Capability):
    """
    代表内部使用 LLM 的代码 Agent (Agentic Tool)。
    Represents a Code Agent (Agentic Tool) that uses LLM internally.
    """
    system_prompt: str = ""
    allowed_tools: List[str] = [] # List of tool names this agent can use
    mcp_config: Optional[Dict[str, Any]] = None # Agent-specific MCP configuration
    
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
        获取此 Agent 允许使用的工具的模式。
        Retrieve schemas for tools that this agent is allowed to use.
        """
        from src.core.registry import global_registry
        return global_registry.get_all_tool_schemas(whitelist=self.allowed_tools)

    def get_context_description(self) -> str:
        """
        Include allowed tools in description for Agents.
        """
        base_desc = f"{self.name} (Agent): {self.description}"
        if self.allowed_tools:
            tools_str = ", ".join(self.allowed_tools)
            base_desc += f" [Tools: {tools_str}]"
        return base_desc


    async def execute(self, instruction: str, context: Optional[str] = None) -> str:
        """
        Agent 的默认执行逻辑：接收指令并进行处理。
        子类可以重写此方法以实现特定逻辑。
        Default execution for an agent: takes an instruction and processes it.
        Subclasses can override this to implement specific logic.
        """
        # This is a placeholder. Real implementation will use the injected context.
        # For debug, we can print what we received if not overridden
        if context:
            print(f"[{self.name}] Received Context: {len(context)} chars")
        
        raise NotImplementedError("Agent execution logic must be implemented")
