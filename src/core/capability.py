from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


# ============================================================================
# 统一参数传递数据结构
# ============================================================================


@dataclass
class AgentPromptContext:
    """
    统一的 Agent Prompt 上下文结构。

    用于内部标准化参数传递，保持外部接口不变。
    所有 Agent 内部使用此结构进行参数传递和处理。

    Usage:
        # 内部构建
        ctx = AgentPromptContext(
            agent_name="web_agent",
            agent_description="...",
            instruction="...",
            ...
        )

        # 外部兼容（保持旧接口）
        ctx = AgentPromptContext.from_legacy_params(
            instruction="...",
            context="...",
            upstream_capabilities="..."
        )
    """

    # ========== 基础信息 ==========
    agent_name: str = ""
    agent_description: str = ""
    agent_type: str = "standard"  # standard/web/gui/bridge

    # ========== 任务信息 ==========
    core_instruction: str = ""  # 核心指令（已简化）
    original_instruction: str = ""  # 原始指令（用于调试）
    task_priority: str = "normal"  # normal/high/low
    task_category: str = "general"  # coding/web/gui/general

    # ========== 上下文信息 ==========
    background_context: str = ""  # 压缩的背景信息
    relevant_history: str = ""  # 相关历史片段

    # ========== 能力信息 ==========
    allowed_tools: List[str] = field(default_factory=list)
    upstream_capabilities: str = ""  # 上级能力树字符串
    tools_summary: str = ""  # 工具摘要（用于 prompt 渲染）

    # ========== 元数据 ==========
    session_id: str = ""
    trace_id: str = ""
    agent_id: str = ""
    timestamp: str = ""

    # ========== 扩展规则 ==========
    additional_rules: List[str] = field(default_factory=list)  # Agent 特殊规则
    constraints: List[str] = field(default_factory=list)  # 约束条件

    # ========== 配置参数 ==========
    language: str = "zh"
    max_iterations: int = 10

    def __post_init__(self):
        """初始化后处理"""
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    @classmethod
    def from_legacy_params(
        cls,
        instruction: str,
        context: Optional[str] = None,
        upstream_capabilities: Optional[str] = None,
        agent_name: str = "",
        agent_description: str = "",
        allowed_tools: Optional[List[str]] = None,
        language: str = "zh",
    ) -> "AgentPromptContext":
        """
        从旧接口参数创建标准化的上下文对象。

        保持外部接口兼容性，内部转换为统一结构。
        """
        return cls(
            # 基础信息
            agent_name=agent_name,
            agent_description=agent_description,
            agent_type="standard",
            # 任务信息
            core_instruction=instruction,
            original_instruction=instruction,
            # 上下文信息
            background_context=context or "",
            # 能力信息
            upstream_capabilities=upstream_capabilities or "",
            allowed_tools=allowed_tools or [],
            tools_summary=", ".join(allowed_tools) if allowed_tools else "None",
            # 配置参数
            language=language,
        )

    def to_legacy_dict(self) -> Dict[str, Any]:
        """
        转换为旧接口参数字典。

        用于与现有代码兼容。
        """
        return {
            "instruction": self.core_instruction,
            "context": self.background_context,
            "upstream_capabilities": self.upstream_capabilities,
        }

    def get_summary(self) -> str:
        """获取上下文摘要（用于调试）"""
        return (
            f"[AgentPromptContext]\n"
            f"  Agent: {self.agent_name} ({self.agent_type})\n"
            f"  Instruction: {self.core_instruction[:100]}...\n"
            f"  Context: {len(self.background_context)} chars\n"
            f"  Upstream Capabilities: {len(self.upstream_capabilities)} chars\n"
            f"  Tools: {self.tools_summary}\n"
            f"  Language: {self.language}\n"
        )


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

    allowed_tools: List[str] = []  # List of tool names this agent can use
    mcp_config: Optional[Dict[str, Any]] = None  # Agent-specific MCP configuration

    def __init__(self):
        self._private_tools: Dict[str, Capability] = {}

    def register_tool(self, tool: Capability):
        """Register a tool exclusively for this agent."""
        self._private_tools[tool.name] = tool
        if tool.name not in self.allowed_tools:
            self.allowed_tools.append(tool.name)

    # 标准系统提示模板 - 所有子 Agent 共用
    STANDARD_SYSTEM_TEMPLATE_ZH = """
## 你的身份
你是 OneAgent 框架中的子代理：{agent_name}
{agent_description}

## 你的任务
{instruction}

## 执行规范
1. 你收到了上级分配的任务，必须尽力完成
2. **在调用任何工具之前，必须输出你的思考过程（Thinking Process）**，分析当前状态和下一步计划
3. 完成任务后，必须调用 `report_status(status="SUCCESS", message="...")` 工具报告结果
3. 如果任务超出你的能力范围，使用 REJECTED 状态并在 message 中说明原因
4. 如果需要上级帮助或额外工具，使用 INTERRUPTED 状态并在 message 中说明需求

## 上级可用能力
以下是上级 Agent 拥有的能力，如果你需要帮助可以请求使用：
{upstream_capabilities}

## 你的工具能力
你必须使用 `report_status(status, message)` 工具来报告任务完成状态。
所有的结果内容、总结、错误详情或拒绝理由都必须包含在 `message` 参数中。
除此之外，你可能拥有其他内置工具能力（如文件操作、代码编辑、Shell 命令等），请查阅系统提供的工具列表并充分利用它们完成任务。

## .OneAgent 目录说明
`.OneAgent/` 目录是所有代理共享的文件系统（Level 2 共享内存）：
- 所有代理都可以读写 `.OneAgent/` 目录下的文件
- 这是跨代理数据持久化和交换的标准位置
- 当编辑文件时，建议优先选择 `.OneAgent/` 目录下的文件
- `.OneAgent/` 目录内容会被 `.gitignore`，适合存储临时和中间结果
- 如果你需要将代码输出保存为文件供其他代理使用，请保存到 `.OneAgent/` 目录

## 背景上下文
{context}
"""

    STANDARD_SYSTEM_TEMPLATE_EN = """
## Your Identity
You are a sub-agent in the OneAgent framework: {agent_name}
{agent_description}

## Your Task
{instruction}

## Execution Protocol
1. You have received a task from your supervisor, you must try your best to complete it
2. **Before calling any tool, you MUST output your thinking process**, analyzing the current state and next steps
3. After completing the task, you MUST call `report_status(status="SUCCESS", message="...")` tool to report the result
3. If the task is out of your scope, use REJECTED status and explain why in the message
4. If you need help from supervisor or additional tools, use INTERRUPTED status and explain in the message

## Upstream Capabilities
The following capabilities are available from your supervisor, request if needed:
{upstream_capabilities}

## Your Tool Capabilities
You MUST use the `report_status(status, message)` tool to report task completion status.
All result content, summaries, error details, or refusal reasons MUST be included in the `message` parameter.
Additionally, you may have other built-in tool capabilities (such as file operations, code editing, shell commands, etc.). Check the system-provided tool list and utilize them fully to complete your task.

## 背景上下文
{context}
"""

    STANDARD_SYSTEM_TEMPLATE_EN = """
## Your Identity
You are a sub-agent in OneAgent framework: {agent_name}
{agent_description}

## Your Task
{instruction}

## Execution Protocol
1. You have received a task from your supervisor, you must try your best to complete it
2. After completing the task, you MUST call `report_status` tool to report results
3. If the task is out of your scope, use REJECTED status and explain why
4. If you need help from supervisor or additional tools, use INTERRUPTED status and explain why

## Upstream Capabilities
The following capabilities are available from your supervisor, request if needed:
{upstream_capabilities}

## Your Tool Capabilities
You MUST use `report_status(status, message)` tool to report task completion status.
Additionally, you may have other built-in tool capabilities (such as file operations, code editing, shell commands, etc.). Check the system-provided tool list and utilize them fully to complete the task.

## .OneAgent Directory Explanation
The `.OneAgent/` directory is a shared file system (Level 2 shared memory) for all agents:
- All agents can read and write files in the `.OneAgent/` directory
- This is the standard location for cross-agent data persistence and exchange
- When editing files, it is recommended to prioritize files in the `.OneAgent/` directory
- `.OneAgent/` directory contents are in `.gitignore`, suitable for storing temporary and intermediate results
- If you need to save code output as a file for other agents to use, please save it to the `.OneAgent/` directory

## 背景上下文
{context}
"""

    # 标准参数定义 - 所有 Agent 都接收这些参数
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "instruction": {
                "type": "string",
                "description": "The core task instruction from the supervisor (processed by compressor).",
            },
            "context": {
                "type": "string",
                "description": "Compressed background context from conversation history.",
            },
            "upstream_capabilities": {
                "type": "string",
                "description": "Tree view of capabilities available from the supervisor.",
            },
        },
        "required": ["instruction"],
    }

    def build_full_prompt(
        self,
        instruction: str = "",
        context: str = "",
        upstream_capabilities: str = "",
        language: str = "zh",
    ) -> str:
        """
        构建完整的系统提示，组合标准模板和自定义提示。
        Build the full system prompt by combining standard template and custom prompt.

        外部接口保持不变，内部转换为统一结构。
        使用统一渲染框架：
        - 标准段：身份、核心指令、背景信息、能力
        - 自定义段：子 Agent 可覆盖 get_custom_sections()
        """
        # 转换为统一结构
        ctx = AgentPromptContext.from_legacy_params(
            instruction=instruction,
            context=context,
            upstream_capabilities=upstream_capabilities,
            agent_name=self.name,
            agent_description=self.description,
            allowed_tools=self.allowed_tools,
            language=language,
        )

        # 使用统一渲染框架构建 Prompt
        return self._build_prompt_from_context(ctx)

    def build_prompt_sections(self, ctx: AgentPromptContext) -> List[str]:
        """
        构建 Prompt 段落列表。

        统一渲染框架：
        - 标准段：身份、核心指令、背景、能力
        - 自定义段：由子 Agent 覆盖 get_custom_sections()

        返回值说明：
        - 返回段落列表
        - 段落顺序：标准段在前，自定义段在后
        - 子 Agent 可覆盖 get_custom_sections() 添加自定义内容
        """
        sections = []

        if ctx.language == "zh":
            sections.append("## 你的身份")
            sections.append(f"你是 OneAgent 框架中的子代理：{ctx.agent_name}")
            sections.append(ctx.agent_description)
            sections.append("")
        else:
            sections.append("## Your Identity")
            sections.append(
                f"You are a sub-agent in OneAgent framework: {ctx.agent_name}"
            )
            sections.append(ctx.agent_description)
            sections.append("")

        if ctx.language == "zh":
            sections.append("## 核心指令")
        else:
            sections.append("## Core Instruction")
        sections.append(ctx.core_instruction or "No task specified")
        sections.append("")

        if ctx.background_context:
            if ctx.language == "zh":
                sections.append("## 背景信息")
            else:
                sections.append("## Background Information")
            sections.append(ctx.background_context)
            sections.append("")

        if ctx.upstream_capabilities:
            if ctx.language == "zh":
                sections.append("## 上级能力")
            else:
                sections.append("## Upstream Capabilities")
            sections.append("以下是上级 Agent 拥有的能力，如果你需要帮助可以请求使用：")
            sections.append(ctx.upstream_capabilities)
            sections.append("")

        if ctx.language == "zh":
            sections.append("## 你的工具能力")
        else:
            sections.append("## Your Tool Capabilities")
        sections.append(
            "你必须使用 `report_status(status, message)` 工具来报告任务完成状态。"
        )
        sections.append(
            "所有的结果内容、总结、错误详情或拒绝理由都必须包含在 `message` 参数中。"
        )
        if ctx.tools_summary != "None":
            sections.append(
                f"除此之外，你可能拥有其他内置工具能力（{ctx.tools_summary}），请查阅系统提供的工具列表并充分利用它们完成任务。"
            )
        sections.append("")

        if ctx.language == "zh":
            sections.append("## .OneAgent 目录说明")
        else:
            sections.append("## .OneAgent Directory Explanation")
        sections.append(
            "`.OneAgent/` 目录是所有代理共享的文件系统（Level 2 共享内存）："
        )
        sections.append("- 所有代理都可以读写 `.OneAgent/` 目录下的文件")
        sections.append("- 这是跨代理数据持久化和交换的标准位置")
        sections.append("- 当编辑文件时，建议优先选择 `.OneAgent/` 目录下的文件")
        sections.append(
            "- `.OneAgent/` 目录内容会被 `.gitignore`，适合存储临时和中间结果"
        )
        sections.append(
            "- 如果你需要将代码输出保存为文件供其他代理使用，请保存到 `.OneAgent/` 目录"
        )
        sections.append("")

        return sections

    def get_custom_sections(self, ctx: AgentPromptContext) -> List[str]:
        """
        获取子 Agent 自定义段落。

        子 Agent 可以覆盖此方法添加自定义内容。
        例如：WebAgent 可以添加文件权限、网页保持逻辑。

        默认返回空列表（无自定义段落）。
        """
        return []

    def _build_prompt_from_context(self, ctx: AgentPromptContext) -> str:
        """
        内部方法：从统一上下文构建 Prompt。

        统一渲染框架：
        1. 构建标准段落
        2. 获取自定义段落（子 Agent 可覆盖）
        3. 合并为完整 Prompt
        """
        # Debug: Log parameter details
        print(f"[{self.name}] 内部参数传递调试:\n{ctx.get_summary()}")

        sections = self.build_prompt_sections(ctx)
        custom_sections = self.get_custom_sections(ctx)

        all_sections = sections + custom_sections

        return "\n".join(all_sections)

    def get_allowed_tool_schemas(self) -> List[Dict[str, Any]]:
        """
        获取此 Agent 允许使用的工具的模式。
        Retrieve schemas for tools that this agent is allowed to use.
        """
        from src.core.registry import global_registry

        # Split allowed tools into private vs global requests
        # Filter whitelist for global registry to avoid warnings
        global_whitelist = [
            name for name in self.allowed_tools if name not in self._private_tools
        ]

        schemas = global_registry.get_all_tool_schemas(whitelist=global_whitelist)

        # Add private tools
        for name, tool in self._private_tools.items():
            schemas.append(tool.to_function_schema())

        return schemas

    def get_context_description(self) -> str:
        """
        Include allowed tools in description for Agents.
        """
        base_desc = f"{self.name} (Agent): {self.description}"
        if self.allowed_tools:
            tools_str = ", ".join(self.allowed_tools)
            base_desc += f" [Tools: {tools_str}]"
        return base_desc

    async def execute(
        self,
        instruction: str,
        context: Optional[str] = None,
        upstream_capabilities: Optional[str] = None,
        **kwargs,  # Accept additional keyword arguments for compatibility with parent class
    ) -> str:
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
            print(
                f"[{self.name}] Received Upstream Capabilities: {len(upstream_capabilities)} chars"
            )

        raise NotImplementedError("Agent execution logic must be implemented")
