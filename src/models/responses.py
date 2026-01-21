"""
响应数据模型
定义 HTTP API 端点的响应数据模型
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class ApiResponse(BaseModel):
    """API 响应基类"""

    status: str = Field(..., description="响应状态")
    message: Optional[str] = Field(None, description="响应消息")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳"
    )


class NestedCallResponse(ApiResponse):
    """嵌套调用响应模型"""

    session_id: Optional[str] = Field(None, description="会话 ID")
    output: Optional[str] = Field(None, description="输出内容（非流式）")
    output_stream_available: bool = Field(default=False, description="是否提供流式输出")


class CapabilitiesResponse(ApiResponse):
    """能力树响应模型"""

    data: Dict[str, Any] = Field(..., description="能力树数据")


class SessionCreatedResponse(ApiResponse):
    """会话创建响应模型"""

    session_id: str = Field(..., description="会话 ID")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="创建时间"
    )


class SessionClosedResponse(ApiResponse):
    """会话关闭响应模型"""

    session_id: str = Field(..., description="会话 ID")
    closed_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="关闭时间"
    )


class ErrorResponse(ApiResponse):
    """错误响应模型"""

    status: str = Field(default="error", description="状态（固定为 error）")
    code: Optional[int] = Field(None, description="错误代码")
    details: Optional[Dict[str, Any]] = Field(None, description="错误详情")


class SSEEvent(BaseModel):
    """Server-Sent Events 事件模型"""

    event: str = Field(..., description="事件类型")
    data: Dict[str, Any] = Field(..., description="事件数据")
    id: Optional[int] = Field(None, description="事件 ID")
    retry: Optional[int] = Field(None, description="重试时间（毫秒）")


class SSEMessageEvent(SSEEvent):
    """SSE 消息事件"""

    event: str = Field(default="message", description="事件类型")
    data: Dict[str, Any] = Field(..., description="消息数据")


class SSECompleteEvent(SSEEvent):
    """SSE 完成事件"""

    event: str = Field(default="complete", description="事件类型")
    data: Dict[str, Any] = Field(..., description="完成数据")


class SSEErrorEvent(SSEEvent):
    """SSE 错误事件"""

    event: str = Field(default="error", description="事件类型")
    data: Dict[str, Any] = Field(..., description="错误数据")
