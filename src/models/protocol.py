"""
协议定义模块
定义 OneAgent 嵌套系统的自定义 JSON 协议
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class MessageType(str, Enum):
    """消息类型枚举"""

    # 协议握手
    HANDSHAKE = "handshake"
    # 心跳
    HEARTBEAT = "heartbeat"
    # 调用 Agent
    CALL_AGENT = "call_agent"
    # 输出
    OUTPUT = "output"
    # 能力树查询
    GET_CAPABILITIES = "get_capabilities"
    # 能力树响应
    CAPABILITIES = "capabilities"
    # 完成
    COMPLETE = "complete"
    # 错误
    ERROR = "error"
    # 连接确认
    CONNECTED = "connected"
    # 心跳响应
    PONG = "pong"


class ProtocolVersion(str, Enum):
    """协议版本"""

    V1_0 = "1.0"


class ProtocolType(str, Enum):
    """协议类型"""

    WS = "ws"  # WebSocket
    HTTP = "http"  # HTTP


# ========== 协议元数据 ==========


class ProtocolMeta(BaseModel):
    """协议元数据"""

    protocol: str = Field(default="OneAgentNested", description="协议名称")
    version: ProtocolVersion = Field(
        default=ProtocolVersion.V1_0, description="协议版本"
    )
    encoding: str = Field(default="UTF-8", description="编码格式")


# ========== 握手消息 ==========


class HandshakeMessage(BaseModel):
    """握手消息"""

    type: MessageType = Field(default=MessageType.HANDSHAKE, description="消息类型")
    protocol: ProtocolType = Field(..., description="协议类型（ws 或 http）")
    agent_id: Optional[str] = Field(None, description="Agent ID")
    session_id: Optional[str] = Field(None, description="会话 ID（续传时必填）")


class ConnectedMessage(BaseModel):
    """连接确认消息"""

    type: MessageType = Field(default=MessageType.CONNECTED, description="消息类型")
    session_id: str = Field(..., description="会话 ID")


# ========== 心跳消息 ==========


class HeartbeatMessage(BaseModel):
    """心跳消息"""

    type: MessageType = Field(default=MessageType.HEARTBEAT, description="消息类型")
    session_id: str = Field(..., description="会话 ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳"
    )


class PongMessage(BaseModel):
    """心跳响应消息"""

    type: MessageType = Field(default=MessageType.PONG, description="消息类型")
    timestamp: Optional[str] = Field(None, description="时间戳")


# ========== 调用消息 ==========


class CallAgentMessage(BaseModel):
    """调用 Agent 消息"""

    type: MessageType = Field(default=MessageType.CALL_AGENT, description="消息类型")
    caller_agent_id: str = Field(..., description="调用者 Agent ID")
    target_agent_id: str = Field(..., description="目标 Agent ID")
    instruction: str = Field(..., description="指令")
    context: str = Field(default="", description="上下文（可选）")
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="附加参数（可选）"
    )
    timeout: int = Field(default=120, description="超时时间（秒）")
    expect_stream: bool = Field(default=True, description="是否期望流式输出")


# ========== 输出消息 ==========


class OutputMessage(BaseModel):
    """输出消息"""

    type: MessageType = Field(default=MessageType.OUTPUT, description="消息类型")
    session_id: str = Field(..., description="会话 ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳"
    )
    content: str = Field(..., description="内容")
    done: bool = Field(default=False, description="是否完成（流式输出时用）")


# ========== 能力树查询消息 ==========


class GetCapabilitiesMessage(BaseModel):
    """能力树查询消息"""

    type: MessageType = Field(
        default=MessageType.GET_CAPABILITIES, description="消息类型"
    )
    agent_id: str = Field(..., description="Agent ID")
    recursive: bool = Field(default=False, description="是否递归查询子节点")


# ========== 能力树响应消息 ==========


class CapabilitiesMessage(BaseModel):
    """能力树响应消息"""

    type: MessageType = Field(default=MessageType.CAPABILITIES, description="消息类型")
    session_id: Optional[str] = Field(None, description="会话 ID")
    data: Dict[str, Any] = Field(..., description="能力树数据")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳"
    )


# ========== 完成消息 ==========


class CompleteMessage(BaseModel):
    """完成消息"""

    type: MessageType = Field(default=MessageType.COMPLETE, description="消息类型")
    session_id: str = Field(..., description="会话 ID")
    result: str = Field(..., description="结果（success 或 error）")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳"
    )


# ========== 错误消息 ==========


class ErrorMessage(BaseModel):
    """错误消息"""

    type: MessageType = Field(default=MessageType.ERROR, description="消息类型")
    message: str = Field(..., description="错误信息")
    code: Optional[int] = Field(None, description="错误代码")
    session_id: Optional[str] = Field(None, description="会话 ID")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="时间戳"
    )


# ========== 辅助函数 ==========


def parse_message(message: Dict[str, Any]) -> BaseModel:
    """
    解析消息字典为对应的消息模型

    Args:
        message: 消息字典

    Returns:
        对应的消息模型实例

    Raises:
        ValueError: 未知消息类型
    """
    msg_type = message.get("type")

    if msg_type == MessageType.HANDSHAKE:
        return HandshakeMessage(**message)
    elif msg_type == MessageType.HEARTBEAT:
        return HeartbeatMessage(**message)
    elif msg_type == MessageType.CALL_AGENT:
        return CallAgentMessage(**message)
    elif msg_type == MessageType.OUTPUT:
        return OutputMessage(**message)
    elif msg_type == MessageType.GET_CAPABILITIES:
        return GetCapabilitiesMessage(**message)
    elif msg_type == MessageType.COMPLETE:
        return CompleteMessage(**message)
    elif msg_type == MessageType.ERROR:
        return ErrorMessage(**message)
    else:
        raise ValueError(f"Unknown message type: {msg_type}")
