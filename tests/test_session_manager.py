"""
会话管理器单元测试
"""

import pytest
import asyncio
from src.models.session import SessionManager, SessionStatus


@pytest.mark.asyncio
async def test_session_manager_initialization():
    """测试会话管理器初始化"""
    manager = SessionManager()

    assert manager.sessions == {}
    assert manager.nested_sessions == {}
    assert manager.default_timeout == 1800
    assert manager.cleanup_interval == 60


@pytest.mark.asyncio
async def test_create_session():
    """测试创建会话"""
    manager = SessionManager()
    await manager.start()

    session = await manager.create_session(parent_agent_id="agent_001", timeout=60)

    assert session.session_id is not None
    assert session.parent_agent_id == "agent_001"
    assert session.status == SessionStatus.ACTIVE
    assert session.session_id in manager.sessions

    await manager.stop()


@pytest.mark.asyncio
async def test_create_nested_session():
    """测试创建嵌套会话"""
    manager = SessionManager()
    await manager.start()

    parent_session = await manager.create_session(
        parent_agent_id="parent_agent", timeout=60
    )

    child_session = await manager.create_session(
        parent_agent_id="child_agent",
        parent_session_id=parent_session.session_id,
        timeout=60,
    )

    assert child_session is not None
    assert child_session.parent_session_id == parent_session.session_id
    assert (
        child_session.session_id in manager.nested_sessions[parent_session.session_id]
    )

    await manager.stop()


@pytest.mark.asyncio
async def test_session_expiration():
    """测试会话过期"""
    manager = SessionManager(cleanup_interval=1, default_timeout=1)
    await manager.start()

    session = await manager.create_session(parent_agent_id="agent_001", timeout=1)

    # Wait for cleanup interval + timeout
    await asyncio.sleep(2.5)

    # Session should be removed after cleanup
    assert session.session_id not in manager.sessions

    await manager.stop()


@pytest.mark.asyncio
async def test_get_session():
    """测试获取会话"""
    manager = SessionManager()
    await manager.start()

    session = await manager.create_session(parent_agent_id="agent_001", timeout=60)

    retrieved_session = await manager.get_session(session.session_id)

    assert retrieved_session.session_id == session.session_id
    assert retrieved_session.parent_agent_id == "agent_001"

    await manager.stop()


@pytest.mark.asyncio
async def test_close_session():
    """测试关闭会话"""
    manager = SessionManager()
    await manager.start()

    session = await manager.create_session(parent_agent_id="agent_001", timeout=60)

    success = await manager.close_session(session.session_id)

    assert success == True

    retrieved_session = await manager.get_session(session.session_id)
    assert retrieved_session.status == SessionStatus.CLOSED

    await manager.stop()


@pytest.mark.asyncio
async def test_get_nested_sessions():
    """测试获取嵌套会话"""
    manager = SessionManager()
    await manager.start()

    parent_session = await manager.create_session(
        parent_agent_id="parent_agent", timeout=60
    )

    child_session_1 = await manager.create_session(
        parent_agent_id="child_agent",
        parent_session_id=parent_session.session_id,
        timeout=60,
    )

    child_session_2 = await manager.create_session(
        parent_agent_id="child_agent",
        parent_session_id=parent_session.session_id,
        timeout=60,
    )

    nested_sessions = await manager.get_nested_sessions(parent_session.session_id)

    assert len(nested_sessions) == 2

    await manager.stop()


@pytest.mark.asyncio
async def test_session_count():
    """测试会话数量"""
    manager = SessionManager()
    await manager.start()

    for i in range(5):
        await manager.create_session(parent_agent_id=f"agent_{i}", timeout=60)

    assert manager.get_session_count() == 5

    await manager.stop()
