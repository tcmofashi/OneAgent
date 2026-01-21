"""
SubOneAgent - 嵌套 OneAgent，支持被父 OneAgent 调用
支持 runtime 工具，对称设计，可调用其他 SubOneAgent
"""

import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator
from src.core.react_agent import ReactAgent
from src.core.registry import global_registry
from src.models.capability_tree import (
    CapabilityType,
    CapabilityTreeBuilder,
)
from src.utils.system_info import format_system_info_for_description


class SubOneAgent(ReactAgent):
    """
    嵌套 OneAgent，支持被父 OneAgent 调用

    特性：
    - 继承 ReactAgent，具有完整的 ReAct 循环能力
    - 支持嵌套调用其他 SubOneAgent
    - 拥有 runtime 工具（单独列出，不嵌入能力树）
    - 对于 Qwen Code 等拥有自有工具的 Agent，在 description 中详细说明
    - 对称设计：所有 OneAgent 可作为父或子 Agent
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
        runtime_tools: Optional[List[Any]] = None,
    ):
        super().__init__()
        self.id = agent_id or str(uuid.uuid4())
        self.name = name or "SubOneAgent"
        base_description = description or "嵌套 OneAgent，支持被父 Agent 调用"
        system_info = format_system_info_for_description()
        self.description = f"{base_description}\n\n系统信息:\n{system_info}"
        self.parent_agent_id = parent_agent_id
        self.runtime_tools = runtime_tools or []
        self.sub_agents: Dict[str, Any] = {}
        self.parent_session_id: Optional[str] = None

    async def register_sub_agent(self, sub_agent: Any):
        self.sub_agents[sub_agent.id] = sub_agent
        sub_agent.parent_agent_id = self.id

    async def call_nested_agent(
        self,
        agent_id: str,
        instruction: str,
        context: str = "",
        parameters: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        parameters = parameters if parameters is not None else {}

        sub_agent = self.sub_agents.get(agent_id)
        if not sub_agent:
            return {"status": "error", "result": f"SubAgent not found: {agent_id}"}

        try:
            result = await sub_agent.execute(instruction=instruction, context=context)

            return {"status": "success", "result": result}
        except Exception as e:
            return {"status": "error", "result": str(e)}

    async def get_capabilities(self, include_children: bool = True) -> Dict[str, Any]:
        agent_type = CapabilityType.SUB_AGENT

        tools = []
        if hasattr(self, "allowed_tools") and self.allowed_tools:
            for tool_name in self.allowed_tools:
                tool = global_registry.get_capability(tool_name)
                if tool:
                    tools.append(tool)

        sub_agents_list = []
        if include_children and self.sub_agents:
            sub_agents_list = list(self.sub_agents.values())

        capabilities = CapabilityTreeBuilder.build_from_agent(
            agent_id=self.id,
            agent_name=self.name,
            agent_type=agent_type,
            agent_description=self.description,
            sub_agents=sub_agents_list,
            tools=tools,
            runtime_tools=self.runtime_tools if self.runtime_tools else None,
        )

        return capabilities.to_dict()

    async def stream_execute(
        self,
        instruction: str,
        context: Optional[str] = None,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> AsyncGenerator[str, None]:
        parameters = parameters if parameters is not None else {}

        yield f"开始执行指令: {instruction}\n"

        if self.runtime_tools:
            yield f"可用 runtime 工具: {', '.join([rt.name for rt in self.runtime_tools])}\n"

        result = await self.execute(
            instruction=instruction, context=context, upstream_capabilities=None
        )

        yield result
