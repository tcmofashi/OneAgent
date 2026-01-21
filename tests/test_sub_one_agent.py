"""
SubOneAgent 单元测试
"""

import pytest
import asyncio
from src.core.sub_one_agent import SubOneAgent


@pytest.mark.asyncio
async def test_sub_one_agent_initialization():
    """测试 SubOneAgent 初始化"""
    sub_agent = SubOneAgent(
        agent_id="test_sub_001", name="TestSubAgent", description="测试 Sub Agent"
    )

    assert sub_agent.id == "test_sub_001"
    assert sub_agent.name == "TestSubAgent"
    assert "测试 Sub Agent" in sub_agent.description
    assert "系统信息:" in sub_agent.description
    assert sub_agent.parent_agent_id is None
    assert sub_agent.runtime_tools == []


@pytest.mark.asyncio
async def test_sub_one_agent_with_parent():
    """测试带父 Agent 的 SubOneAgent"""
    sub_agent = SubOneAgent(
        agent_id="test_sub_002",
        name="TestSubAgent",
        description="测试 Sub Agent",
        parent_agent_id="parent_agent_001",
    )

    assert sub_agent.parent_agent_id == "parent_agent_001"


@pytest.mark.asyncio
async def test_sub_one_agent_with_runtime_tools():
    """测试带 runtime 工具的 SubOneAgent"""
    sub_agent = SubOneAgent(
        agent_id="test_sub_003",
        name="TestSubAgent",
        description="测试 Sub Agent",
        runtime_tools=["tool1", "tool2"],
    )

    assert len(sub_agent.runtime_tools) == 2
    assert sub_agent.runtime_tools == ["tool1", "tool2"]


@pytest.mark.asyncio
async def test_register_sub_agent():
    """测试注册子 Agent"""
    parent_agent = SubOneAgent()
    child_agent = SubOneAgent(
        agent_id="test_child_001", name="TestChildAgent", description="测试 Child Agent"
    )

    await parent_agent.register_sub_agent(child_agent)

    assert child_agent.id in parent_agent.sub_agents
    assert parent_agent.sub_agents[child_agent.id] == child_agent
    assert child_agent.parent_agent_id == parent_agent.id


@pytest.mark.asyncio
async def test_call_nested_agent_not_found():
    """测试调用不存在的子 Agent"""
    parent_agent = SubOneAgent()

    result = await parent_agent.call_nested_agent(
        agent_id="non_existent", instruction="测试"
    )

    assert result["status"] == "error"
    assert "not found" in result["result"]


@pytest.mark.asyncio
async def test_call_nested_agent_success():
    """测试成功调用子 Agent"""
    parent_agent = SubOneAgent()

    child_agent = SubOneAgent(
        agent_id="test_child_002", name="TestChildAgent", description="测试 Child Agent"
    )

    # Mock the execute method to return a fixed result
    async def mock_execute(instruction, context=None, upstream_capabilities=None):
        return "子 Agent 执行结果"

    child_agent.execute = mock_execute

    await parent_agent.register_sub_agent(child_agent)

    result = await parent_agent.call_nested_agent(
        agent_id=child_agent.id, instruction="测试指令"
    )

    if result["status"] != "success":
        print(f"DEBUG: Error result: {result}")
    assert result["status"] == "success"
    assert result["result"] == "子 Agent 执行结果"


@pytest.mark.asyncio
async def test_get_capabilities():
    """测试获取能力树"""
    sub_agent = SubOneAgent(
        agent_id="test_sub_004", name="TestSubAgent", description="测试 Sub Agent"
    )

    capabilities = await sub_agent.get_capabilities(include_children=False)

    assert "agent" in capabilities
    assert capabilities["agent"]["id"] == "test_sub_004"
    assert capabilities["agent"]["name"] == "TestSubAgent"
    assert "children" in capabilities
    assert "runtime_tools" in capabilities


@pytest.mark.asyncio
async def test_stream_execute():
    """测试流式执行"""
    sub_agent = SubOneAgent(
        agent_id="test_sub_005", name="TestSubAgent", description="测试 Sub Agent"
    )

    # Mock the execute method to return a fixed result
    async def mock_execute(instruction, context=None, upstream_capabilities=None):
        return "执行结果"

    sub_agent.execute = mock_execute

    chunks = []
    async for chunk in sub_agent.stream_execute(instruction="测试指令"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert any("开始执行指令" in chunk for chunk in chunks)
    assert any("执行结果" in chunk for chunk in chunks)
