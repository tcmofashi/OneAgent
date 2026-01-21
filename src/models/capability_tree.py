"""
能力树数据结构
定义 OneAgent 嵌套系统的能力树（runtime 工具单独列出）
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class CapabilityType(str, Enum):
    """能力类型"""

    ROOT_AGENT = "root_agent"
    SUB_AGENT = "sub_agent"
    TOOL = "tool"


class CapabilityTreeNode(BaseModel):
    """能力树节点（不包括 runtime 工具）"""

    id: str = Field(..., description="能力 ID")
    name: str = Field(..., description="能力名称")
    description: str = Field(..., description="能力描述")
    type: CapabilityType = Field(..., description="能力类型")
    parent_id: Optional[str] = Field(None, description="父节点 ID")
    children: List["CapabilityTreeNode"] = Field(
        default_factory=list, description="子节点列表"
    )
    parameters: Dict[str, Any] = Field(default_factory=dict, description="能力参数")

    class Config:
        arbitrary_types_allowed = True


class RuntimeTool(BaseModel):
    """Runtime 工具（单独列出，不嵌入能力树）"""

    id: str = Field(..., description="工具 ID")
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="工具参数")


class NestedAgentCapabilities(BaseModel):
    """嵌套 OneAgent 能力集合

    注意：
    - children 包含子 OneAgent 和普通工具（不包括 runtime 工具）
    - runtime_tools 单独列出 SubOneAgent 的 runtime 工具
    - 对于 Qwen Code 等拥有大量自有工具的 Agent，在 agent.description 中详细说明
    """

    agent: CapabilityTreeNode = Field(..., description="根节点（自身）")
    children: List[CapabilityTreeNode] = Field(
        default_factory=list, description="子 OneAgent 和工具（不包括 runtime）"
    )
    runtime_tools: List[RuntimeTool] = Field(
        default_factory=list, description="Runtime 工具列表（单独列出）"
    )

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "agent": self.agent.dict(),
            "children": [child.dict() for child in self.children],
            "runtime_tools": [tool.dict() for tool in self.runtime_tools],
        }


class CapabilityTreeBuilder:
    """能力树构建器"""

    @staticmethod
    def build_from_agent(
        agent_id: str,
        agent_name: str,
        agent_type: CapabilityType,
        agent_description: str,
        sub_agents: List[Any],
        tools: List[Any],
        runtime_tools: Optional[List[Any]] = None,
    ) -> NestedAgentCapabilities:
        """
        从 Agent 构建能力树

        Args:
            agent_id: Agent ID
            agent_name: Agent 名称
            agent_type: Agent 类型
            agent_description: Agent 描述（对于 Qwen Code 等，在此详细说明自有工具）
            sub_agents: 子 OneAgent 列表
            tools: 工具列表
            runtime_tools: Runtime 工具列表（可选）

        Returns:
            嵌套 Agent 能力集合
        """
        # 构建根节点
        root_node = CapabilityTreeNode(
            id=agent_id,
            name=agent_name,
            description=agent_description,
            type=agent_type,
            parent_id=None,
            children=[],
        )

        # 构建子节点（SubOneAgent 和普通工具）
        children = []
        for sub_agent in sub_agents:
            children.append(
                CapabilityTreeNode(
                    id=sub_agent.id,
                    name=sub_agent.name,
                    description=sub_agent.description,
                    type=CapabilityType.SUB_AGENT,
                    parent_id=agent_id,
                    children=[],
                )
            )

        for tool in tools:
            children.append(
                CapabilityTreeNode(
                    id=tool.name,
                    name=tool.name,
                    description=tool.description,
                    type=CapabilityType.TOOL,
                    parent_id=agent_id,
                    parameters={
                        "input_schema": tool.input_schema.model_dump()
                        if hasattr(tool, "input_schema")
                        else {}
                    },
                )
            )

        # 构建 runtime 工具列表
        runtime_tools_list = []
        if runtime_tools:
            for rt_tool in runtime_tools:
                runtime_tools_list.append(
                    RuntimeTool(
                        id=rt_tool.name,
                        name=rt_tool.name,
                        description=rt_tool.description,
                        parameters={
                            "input_schema": rt_tool.input_schema.model_dump()
                            if hasattr(rt_tool, "input_schema")
                            else {}
                        },
                    )
                )

        return NestedAgentCapabilities(
            agent=root_node, children=children, runtime_tools=runtime_tools_list
        )

    @staticmethod
    def merge_capabilities(
        parent_capabilities: NestedAgentCapabilities,
        child_capabilities: NestedAgentCapabilities,
    ) -> NestedAgentCapabilities:
        """
        合并父子能力树

        Args:
            parent_capabilities: 父 Agent 能力树
            child_capabilities: 子 Agent 能力树

        Returns:
            合并后的能力树
        """
        # 复制父节点的子节点列表
        merged_children = parent_capabilities.children.copy()

        # 添加子能力树
        merged_children.append(child_capabilities.agent)

        return NestedAgentCapabilities(
            agent=parent_capabilities.agent,
            children=merged_children,
            runtime_tools=parent_capabilities.runtime_tools,
        )
