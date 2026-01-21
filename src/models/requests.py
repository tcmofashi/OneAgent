"""
请求数据模型
定义 HTTP API 端点的请求数据模型
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class NestedCallRequest(BaseModel):
    """嵌套调用请求模型"""

    agent_id: str = Field(..., description="目标 Agent ID")
    instruction: str = Field(..., description="指令")
    context: str = Field(default="", description="上下文")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="附加参数")
    timeout: int = Field(default=120, ge=1, le=3600, description="超时时间（秒）")
    expect_stream: bool = Field(default=True, description="是否期望流式输出")
    caller_agent_id: Optional[str] = Field(None, description="调用者 Agent ID（可选）")


class GetCapabilitiesRequest(BaseModel):
    """能力树查询请求模型"""

    agent_id: str = Field(..., description="Agent ID")
    recursive: bool = Field(default=False, description="是否递归查询子节点")


class CreateSessionRequest(BaseModel):
    """创建会话请求模型"""

    parent_agent_id: str = Field(..., description="父 Agent ID")
    parent_session_id: Optional[str] = Field(None, description="父会话 ID（用于嵌套）")
    timeout: int = Field(
        default=1800, ge=60, le=86400, description="会话超时时间（秒）"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")


class CloseSessionRequest(BaseModel):
    """关闭会话请求模型"""

    session_id: str = Field(..., description="会话 ID")


class HeartbeatRequest(BaseModel):
    """心跳请求模型"""

    session_id: str = Field(..., description="会话 ID")
