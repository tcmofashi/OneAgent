"""
RootOneAgent 单元测试
"""

import pytest
import asyncio
from src.core.root_one_agent import RootOneAgent
from src.core.sub_one_agent import SubOneAgent
from src.models.session import SessionStatus


@pytest.mark.asyncio
async def test_root_one_agent_initialization():
    """测试 RootOneAgent 初始化"""
    root_agent = RootOneAgent(
        agent_id="test_root_001",
        name="TestRootAgent",
        description="测试 Root Agent",
    )

    assert root_agent.id == "test_root_001"
    assert root_agent.name == "TestRootAgent"
    assert "测试 Root Agent" in root_agent.description
    assert "系统信息:" in root_agent.description
    assert root_agent.session_manager is not None


@pytest.mark.asyncio
async def test_root_one_agent_start_stop():
    """测试 RootOneAgent 启动和停止"""
    root_agent = RootOneAgent()

    await root_agent.start()
    assert root_agent._started == True

    await root_agent.stop()
    assert root_agent._started == False


@pytest.mark.asyncio
async def test_register_sub_agent():
    """测试注册子 Agent"""
    root_agent = RootOneAgent()
    await root_agent.start()

    sub_agent = SubOneAgent(
        agent_id="test_sub_001",
        name="TestSubAgent",
        description="测试 Sub Agent",
        parent_agent_id=root_agent.id,
    )

    await root_agent.register_sub_agent(sub_agent)

    assert sub_agent.id in root_agent.sub_agents
    assert root_agent.sub_agents[sub_agent.id] == sub_agent
    assert sub_agent.parent_agent_id == root_agent.id

    await root_agent.stop()


@pytest.mark.asyncio
async def test_call_nested_agent_not_found():
    """测试调用不存在的子 Agent"""
    root_agent = RootOneAgent()
    await root_agent.start()

    result = await root_agent.call_nested_agent(
        agent_id="non_existent_agent", instruction="测试", timeout=60
    )

    assert result["status"] == "error"
    assert "not found" in result["result"]

    await root_agent.stop()


@pytest.mark.asyncio
async def test_call_nested_agent_success():
    """测试成功调用子 Agent"""
    root_agent = RootOneAgent()
    await root_agent.start()

    sub_agent = SubOneAgent(
        agent_id="test_sub_002", name="TestSubAgent", description="测试 Sub Agent"
    )

    async def mock_execute(
        instruction, context=None, upstream_capabilities=None, parameters=None
    ):
        return "执行结果"

    sub_agent.execute = mock_execute

    await root_agent.register_sub_agent(sub_agent)

    result = await root_agent.call_nested_agent(
        agent_id=sub_agent.id, instruction="测试指令", timeout=60, expect_stream=False
    )

    assert result["status"] == "success"
    assert result["result"] == "执行结果"
    assert result["output_stream"] is None

    await root_agent.stop()


@pytest.mark.asyncio
async def test_get_capabilities_tree_root():
    """测试获取 RootOneAgent 能力树"""
    root_agent = RootOneAgent()
    await root_agent.start()

    capabilities = await root_agent.get_capabilities_tree(
        agent_id=root_agent.id, recursive=False
    )

    assert "agent" in capabilities
    assert capabilities["agent"]["id"] == root_agent.id
    assert capabilities["agent"]["name"] == "RootOneAgent"
    assert "children" in capabilities
    assert "runtime_tools" in capabilities

    await root_agent.stop()


@pytest.mark.asyncio
async def test_create_nested_session():
    """测试创建嵌套会话"""
    root_agent = RootOneAgent()
    await root_agent.start()

    session_id = await root_agent.create_nested_session(
        parent_agent_id=root_agent.id, timeout=60, metadata={"test": True}
    )

    assert session_id is not None
    assert len(session_id) > 0

    session = await root_agent.get_session(session_id)
    assert session is not None
    assert session.parent_agent_id == root_agent.id
    assert session.metadata == {"test": True}

    await root_agent.stop()


@pytest.mark.asyncio
async def test_close_nested_session():
    """测试关闭嵌套会话"""
    root_agent = RootOneAgent()
    await root_agent.start()

    session_id = await root_agent.create_nested_session(parent_agent_id=root_agent.id)

    success = await root_agent.close_nested_session(session_id)

    assert success == True

    session = await root_agent.get_session(session_id)
    assert session.status == SessionStatus.CLOSED

    await root_agent.stop()
