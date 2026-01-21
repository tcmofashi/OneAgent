"""
会话数据模型和管理器
管理嵌套 OneAgent 系统的会话生命周期
"""

import asyncio
import uuid
from datetime import datetime
from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field


class SessionStatus(str, Enum):
    """会话状态"""

    ACTIVE = "active"
    CLOSED = "closed"
    ERROR = "error"
    TIMEOUT = "timeout"


class Session(BaseModel):
    """会话对象"""

    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), description="会话 ID"
    )
    parent_session_id: Optional[str] = Field(None, description="父会话 ID（用于嵌套）")
    parent_agent_id: str = Field(..., description="父 Agent ID")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="创建时间"
    )
    last_activity: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="最后活动时间",
    )
    status: SessionStatus = Field(default=SessionStatus.ACTIVE, description="会话状态")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="会话元数据")
    timeout: int = Field(default=1800, description="超时时间（秒）")

    def update_activity(self):
        """更新最后活动时间"""
        self.last_activity = datetime.utcnow().isoformat()

    def is_expired(self) -> bool:
        """检查会话是否过期"""
        created_time = datetime.fromisoformat(self.created_at)
        elapsed = (datetime.utcnow() - created_time).total_seconds()
        return elapsed > self.timeout

    def close(self):
        """关闭会话"""
        self.status = SessionStatus.CLOSED
        self.last_activity = datetime.utcnow().isoformat()


class SessionManager:
    """会话管理器"""

    def __init__(self, cleanup_interval: int = 60, default_timeout: int = 1800):
        """
        初始化会话管理器

        Args:
            cleanup_interval: 清理间隔（秒）
            default_timeout: 默认超时时间（秒）
        """
        self.sessions: Dict[str, Session] = {}
        self.nested_sessions: Dict[str, List[str]] = {}
        self.cleanup_interval = cleanup_interval
        self.default_timeout = default_timeout
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start(self):
        """启动会话管理器"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        """停止会话管理器"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None

    async def _cleanup_loop(self):
        """清理循环"""
        while True:
            try:
                await asyncio.sleep(self.cleanup_interval)
                await self._cleanup_expired_sessions()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"清理会话时出错: {e}")

    async def _cleanup_expired_sessions(self):
        """清理过期会话"""
        expired_session_ids = [
            session_id
            for session_id, session in self.sessions.items()
            if session.is_expired() or session.status != SessionStatus.ACTIVE
        ]

        for session_id in expired_session_ids:
            await self.close_session(session_id, reason="expired")
            self.sessions.pop(session_id, None)

    async def create_session(
        self,
        parent_agent_id: str,
        parent_session_id: Optional[str] = None,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        创建会话

        Args:
            parent_agent_id: 父 Agent ID
            parent_session_id: 父会话 ID（用于嵌套）
            timeout: 超时时间（秒）
            metadata: 会话元数据

        Returns:
            会话对象
        """
        session = Session(
            parent_agent_id=parent_agent_id,
            parent_session_id=parent_session_id,
            timeout=timeout or self.default_timeout,
            metadata=metadata or {},
        )

        self.sessions[session.session_id] = session

        if parent_session_id:
            if parent_session_id not in self.nested_sessions:
                self.nested_sessions[parent_session_id] = []
            self.nested_sessions[parent_session_id].append(session.session_id)

        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        获取会话

        Args:
            session_id: 会话 ID

        Returns:
            会话对象，如果不存在则返回 None
        """
        session = self.sessions.get(session_id)
        if session:
            session.update_activity()
        return session

    async def close_session(self, session_id: str, reason: str = "closed") -> bool:
        """
        关闭会话

        Args:
            session_id: 会话 ID
            reason: 关闭原因

        Returns:
            是否成功关闭
        """
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.close()
        session.metadata["close_reason"] = reason

        # 递归关闭子会话
        if session_id in self.nested_sessions:
            child_session_ids = self.nested_sessions[session_id]
            for child_id in child_session_ids:
                await self.close_session(child_id, reason="parent_closed")
            del self.nested_sessions[session_id]

        # 从父会话的嵌套列表中移除
        if session.parent_session_id:
            if session.parent_session_id in self.nested_sessions:
                if session_id in self.nested_sessions[session.parent_session_id]:
                    self.nested_sessions[session.parent_session_id].remove(session_id)

        return True

    async def get_nested_sessions(self, parent_session_id: str) -> List[Session]:
        """
        获取父会话的所有子会话

        Args:
            parent_session_id: 父会话 ID

        Returns:
            子会话列表
        """
        child_session_ids = self.nested_sessions.get(parent_session_id, [])
        return [
            self.sessions[child_id]
            for child_id in child_session_ids
            if child_id in self.sessions
        ]

    async def get_active_sessions(self) -> List[Session]:
        """
        获取所有活跃会话

        Returns:
            活跃会话列表
        """
        return [
            session
            for session in self.sessions.values()
            if session.status == SessionStatus.ACTIVE
        ]

    def get_session_count(self) -> int:
        """
        获取会话总数

        Returns:
            会话总数
        """
        return len(self.sessions)
