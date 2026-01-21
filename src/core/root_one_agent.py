"""
RootOneAgent - 顶层 OneAgent，支持嵌套编排
基于 Orchestrator 扩展，提供嵌套调用、能力树查询、会话管理等功能
"""

import uuid
from typing import Dict, Any, Optional
from src.core.orchestrator import Orchestrator
from src.core.registry import global_registry
from src.models.session import SessionManager
from src.models.capability_tree import (
    NestedAgentCapabilities,
    CapabilityType,
    CapabilityTreeBuilder,
)
from src.utils.system_info import format_system_info_for_description


class RootOneAgent(Orchestrator):
    """
    顶层 OneAgent，具备嵌套编排和外部 API 能力

    特性：
    - 嵌套调用其他 SubOneAgent
    - 查询能力树（runtime 工具单独列出）
    - 管理嵌套会话
    - 提供 API 网关接口
    """

    def __init__(
        self,
        agent_id: Optional[str] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ):
        """
        初始化 RootOneAgent

        Args:
            agent_id: Agent ID（默认生成 UUID）
            name: Agent 名称（默认 "RootOneAgent"）
            description: Agent 描述（默认 "顶层 OneAgent，支持嵌套编排和外部 API"）
        """
        super().__init__()
        self.id = agent_id or str(uuid.uuid4())
        self.name = name or "RootOneAgent"
        base_description = description or "顶层 OneAgent，支持嵌套编排和外部 API"
        system_info = format_system_info_for_description()
        self.description = f"{base_description}\n\n系统信息:\n{system_info}"
        self.session_manager = SessionManager()
        self.sub_agents: Dict[str, Any] = {}
        self._started = False

    async def start(self):
        """启动 RootOneAgent"""
        if not self._started:
            await self.session_manager.start()
            self._started = True

    async def stop(self):
        """停止 RootOneAgent"""
        if self._started:
            await self.session_manager.stop()
            self._started = False

    async def register_sub_agent(self, sub_agent: Any):
        """
        注册子 OneAgent

        Args:
            sub_agent: SubOneAgent 实例
        """
        self.sub_agents[sub_agent.id] = sub_agent

    async def call_nested_agent(
        self,
        agent_id: str,
        instruction: str,
        context: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        timeout: int = 120,
        expect_stream: bool = False,
    ) -> Dict[str, Any]:
        """
        调用嵌套的 OneAgent

        Args:
            agent_id: 目标 SubOneAgent ID
            instruction: 指令
            context: 上下文
            parameters: 附加参数
            timeout: 超时时间（秒）
            expect_stream: 是否期望流式输出

        Returns:
            {
                "status": "success" | "error",
                "result": str,
                "output_stream": AsyncGenerator[str] | None
            }
        """
        parameters = parameters if parameters is not None else {}

        sub_agent = self.sub_agents.get(agent_id)
        if not sub_agent:
            return {"status": "error", "result": f"SubAgent not found: {agent_id}"}

        try:
            if expect_stream:
                return {
                    "status": "success",
                    "result": None,
                    "output_stream": sub_agent.stream_execute(
                        instruction=instruction, context=context
                    ),
                }
            else:
                result = await sub_agent.execute(
                    instruction=instruction, context=context
                )

                return {"status": "success", "result": result, "output_stream": None}

        except Exception as e:
            return {"status": "error", "result": str(e), "output_stream": None}

    async def get_capabilities_tree(
        self, agent_id: Optional[str] = None, recursive: bool = False
    ) -> Dict[str, Any]:
        """
        查询指定 OneAgent 的能力树

        Args:
            agent_id: Agent ID 或名称（如果为空，返回 RootOneAgent 的能力树）
            recursive: 是否递归查询子节点

        Returns:
            {
                "agent": {...},
                "children": [...],
                "runtime_tools": [...]
            }
        """
        target_agent = None

        if (
            agent_id is None
            or agent_id == ""
            or str(agent_id) == str(self.id)
            or agent_id == self.name
        ):
            target_agent = self
        else:
            target_agent = self.sub_agents.get(agent_id)
            if not target_agent:
                for sub_agent in self.sub_agents.values():
                    if sub_agent.name == agent_id:
                        target_agent = sub_agent
                        break

        if not target_agent:
            raise ValueError(f"Agent not found: {agent_id}")

        capabilities = await self._build_capabilities_for_agent(
            agent=target_agent, recursive=recursive
        )

        return capabilities.to_dict()

    async def _build_capabilities_for_agent(
        self, agent: Any, recursive: bool = False
    ) -> NestedAgentCapabilities:
        """
        为指定 Agent 构建能力树

        Args:
            agent: Agent 实例
            recursive: 是否递归查询子节点

        Returns:
            嵌套 Agent 能力集合
        """
        agent_type = (
            CapabilityType.ROOT_AGENT
            if agent.id == self.id
            else CapabilityType.SUB_AGENT
        )

        # 获取工具列表
        tools = []
        if hasattr(agent, "allowed_tools") and agent.allowed_tools:
            for tool_name in agent.allowed_tools:
                tool = global_registry.get_capability(tool_name)
                if tool:
                    tools.append(tool)

        # 获取 runtime 工具列表（仅 SubOneAgent）
        runtime_tools = []
        if hasattr(agent, "runtime_tools") and agent.runtime_tools:
            runtime_tools = agent.runtime_tools

        # 获取子 Agent 列表
        sub_agents_list = []
        if recursive and hasattr(agent, "sub_agents") and agent.sub_agents:
            sub_agents_list = list(agent.sub_agents.values())

        # 构建能力树
        capabilities = CapabilityTreeBuilder.build_from_agent(
            agent_id=agent.id,
            agent_name=agent.name,
            agent_type=agent_type,
            agent_description=agent.description,
            sub_agents=sub_agents_list,
            tools=tools,
            runtime_tools=runtime_tools if runtime_tools else None,
        )

        return capabilities

    async def create_nested_session(
        self,
        parent_agent_id: str,
        parent_session_id: Optional[str] = None,
        timeout: int = 1800,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        创建嵌套会话

        Args:
            parent_agent_id: 父 Agent ID
            parent_session_id: 父会话 ID（用于嵌套）
            timeout: 超时时间（秒）
            metadata: 会话元数据

        Returns:
            会话 ID
        """
        session = await self.session_manager.create_session(
            parent_agent_id=parent_agent_id,
            parent_session_id=parent_session_id,
            timeout=timeout,
            metadata=metadata,
        )

        return session.session_id

    async def close_nested_session(
        self, session_id: str, reason: str = "closed"
    ) -> bool:
        """
        关闭嵌套会话

        Args:
            session_id: 会话 ID
            reason: 关闭原因

        Returns:
            是否成功关闭
        """
        return await self.session_manager.close_session(session_id, reason=reason)

    async def get_session(self, session_id: str):
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            会话对象，如果不存在则返回 None
        """
        return await self.session_manager.get_session(session_id)
