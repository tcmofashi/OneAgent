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
    
    标准子 Agent 工作流：
    - 输入：instruction (核心指令), context (压缩上下文), upstream_capabilities (上级能力树)
    - 工具：report_status (必须调用以结束执行)
    - 输出：通过 report_status 返回 SUCCESS/FAILURE/REJECTED/INTERRUPTED
    """
    system_prompt: str = ""  # 子 Agent 自定义的系统提示
    allowed_tools: List[str] = []  # List of tool names this agent can use
    mcp_config: Optional[Dict[str, Any]] = None  # Agent-specific MCP configuration
    
    # 标准系统提示模板 - 所有子 Agent 共用
    STANDARD_SYSTEM_TEMPLATE_ZH = """
## 你的身份
你是 OneAgent 框架中的子代理：{agent_name}
{agent_description}

## 执行规范
1. 你收到了上级分配的任务，必须尽力完成
2. 完成任务后，必须调用 `report_status` 工具报告结果
3. 如果任务超出你的能力范围，使用 REJECTED 状态并说明原因
4. 如果需要上级帮助或额外工具，使用 INTERRUPTED 状态

## 上级可用能力
以下是上级 Agent 拥有的能力，如果你需要帮助可以请求使用：
{upstream_capabilities}

## 你的可用工具
{allowed_tools}

## 背景上下文
{context}

## 你的专属指令
{custom_prompt}
"""
    
    STANDARD_SYSTEM_TEMPLATE_EN = """
## Your Identity
You are a sub-agent in the OneAgent framework: {agent_name}
{agent_description}

## Execution Protocol
1. You have received a task from your supervisor, you must try your best to complete it
2. After completing the task, you MUST call `report_status` tool to report the result
3. If the task is out of your scope, use REJECTED status and explain why
4. If you need help from supervisor or additional tools, use INTERRUPTED status

## Upstream Capabilities
The following capabilities are available from your supervisor, request if needed:
{upstream_capabilities}

## Your Available Tools
{allowed_tools}

## Background Context
{context}

## Your Custom Instructions
{custom_prompt}
"""
    
    # 标准参数定义 - 所有 Agent 都接收这些参数
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "The core task instruction from the supervisor (processed by compressor)."
            },
            "context": {
                "type": "string",
                "description": "Compressed background context from conversation history."
            },
            "upstream_capabilities": {
                "type": "string",
                "description": "Tree view of capabilities available from the supervisor."
            }
        },
        "required": ["instruction"]
    }

    def build_full_prompt(self, context: str = "", upstream_capabilities: str = "", language: str = "zh") -> str:
        """
        构建完整的系统提示，组合标准模板和自定义提示。
        Build the full system prompt by combining standard template and custom prompt.
        """
        template = self.STANDARD_SYSTEM_TEMPLATE_ZH if language == "zh" else self.STANDARD_SYSTEM_TEMPLATE_EN
        
        # 格式化工具列表
        tools_str = ", ".join(self.allowed_tools) if self.allowed_tools else "None"
        
        return template.format(
            agent_name=self.name,
            agent_description=self.description,
            upstream_capabilities=upstream_capabilities or "None provided",
            allowed_tools=tools_str,
            context=context or "No additional context",
            custom_prompt=self.system_prompt or "No custom instructions"
        )

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


    async def execute(self, instruction: str, context: Optional[str] = None, upstream_capabilities: Optional[str] = None) -> str:
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
        if upstream_capabilities:
            print(f"[{self.name}] Received Upstream Capabilities: {len(upstream_capabilities)} chars")
        
        raise NotImplementedError("Agent execution logic must be implemented")

