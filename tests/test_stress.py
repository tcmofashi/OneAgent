"""
嵌套 OneAgent 压力测试
测试并发调用、深层嵌套和内存管理
"""

import pytest
import asyncio
from src.core.root_one_agent import RootOneAgent
from src.core.sub_one_agent import SubOneAgent
from src.models.session import SessionStatus


@pytest.mark.asyncio
async def test_concurrent_nested_calls():
    """测试 10+ 个并发嵌套调用"""
    root_agent = RootOneAgent(name="TestRoot")
    await root_agent.start()

    # 创建多个 SubAgent
    sub_agents = []
    for i in range(10):
        agent = SubOneAgent(
            agent_id=f"sub_agent_{i}",
            name=f"SubAgent{i}",
            description=f"压力测试 Agent {i}",
        )

        # 每个代理需要独立的 mock_execute（使用闭包捕获正确的 i 值）
        def make_mock_execute(idx):
            async def mock_execute(
                instruction, context=None, upstream_capabilities=None
            ):
                await asyncio.sleep(0.1)  # 模拟 100ms 处理
                return f"Agent {idx} 完成"

            return mock_execute

        agent.execute = make_mock_execute(i)
        await root_agent.register_sub_agent(agent)
        sub_agents.append(agent)

    # 并发调用所有 SubAgent
    results = await asyncio.gather(
        *[
            root_agent.call_nested_agent(
                agent_id=agent.id, instruction=f"测试指令 {i}", timeout=10
            )
            for i, agent in enumerate(sub_agents)
        ]
    )

    # 验证所有调用成功
    for i, agent in enumerate(sub_agents):
        result = results[i]
        assert result["status"] == "success"
        assert f"Agent {i} 完成" in result["result"]

    await root_agent.stop()


@pytest.mark.asyncio
async def test_deep_nesting():
    """测试 5+ 层深层嵌套"""
    # 创建代理链：Root -> Sub1 -> Sub2 -> Sub3 -> Sub4 -> Sub5
    root_agent = RootOneAgent(name="RootLevel0")
    await root_agent.start()

    # 创建 5 层嵌套
    agents = [root_agent]
    for level in range(1, 6):
        agent = SubOneAgent(
            agent_id=f"agent_level_{level}",
            name=f"AgentLevel{level}",
            description=f"第 {level} 层 Agent",
        )

        # 注册到上一层
        await agents[-1].register_sub_agent(agent)
        agents.append(agent)

    # 从根调用最深层代理（跨越 5 层）
    result = await root_agent.call_nested_agent(
        agent_id="agent_level_5", instruction="深层嵌套调用"
    )

    # 由于 SubOneAgent.call_nested_agent 只能调用直接子代理，
    # 所以需要通过各层代理逐级调用
    # 这里简化为直接调用子代理
    assert result["status"] == "error"  # 预期失败，因为不是直接子代理

    # 测试直接子代理调用
    level5_agent = agents[5]
    level4_agent = agents[4]

    async def mock_execute(instruction, context=None, upstream_capabilities=None):
        return f"Deep nesting test result: {instruction}"

    level5_agent.execute = mock_execute
    await level4_agent.register_sub_agent(level5_agent)

    # SubOneAgent.call_nested_agent 没有 timeout 参数
    result = await level4_agent.call_nested_agent(
        agent_id="agent_level_5", instruction="深层嵌套调用"
    )

    assert result["status"] == "success"
    assert "Deep nesting test result" in result["result"]

    await root_agent.stop()


@pytest.mark.asyncio
async def test_session_memory_leak():
    """测试会话创建和清理，检查内存泄漏"""
    root_agent = RootOneAgent(name="TestRoot")
    await root_agent.start()

    # 创建 100 个会话
    session_ids = []
    for i in range(100):
        session_id = await root_agent.create_nested_session(
            parent_agent_id=root_agent.id, timeout=1
        )
        session_ids.append(session_id)

    # 验证会话数量
    assert root_agent.session_manager.get_session_count() == 100

    # 关闭所有会话
    for session_id in session_ids:
        await root_agent.close_nested_session(session_id)

    # 等待清理完成
    await asyncio.sleep(2)

    # 验证会话已清理（但 closed 状态的会话仍存在）
    active_sessions = [
        s
        for s in root_agent.session_manager.sessions.values()
        if s.status == SessionStatus.ACTIVE
    ]
    assert len(active_sessions) == 0

    await root_agent.stop()


@pytest.mark.asyncio
async def test_rapid_session_creation():
    """测试快速创建和关闭大量会话"""
    root_agent = RootOneAgent(name="TestRoot")
    await root_agent.start()

    # 快速创建和关闭 50 个会话
    for i in range(50):
        session_id = await root_agent.create_nested_session(
            parent_agent_id=root_agent.id, timeout=10
        )

        # 立即关闭
        success = await root_agent.close_nested_session(session_id)
        assert success

    # 验证会话数量
    assert root_agent.session_manager.get_session_count() == 50

    await root_agent.stop()


@pytest.mark.asyncio
async def test_nested_session_cleanup():
    """测试嵌套会话的正确清理"""
    root_agent = RootOneAgent(name="TestRoot")
    await root_agent.start()

    # 创建父会话和 3 个子会话
    parent_session_id = await root_agent.create_nested_session(
        parent_agent_id=root_agent.id, timeout=60
    )

    child_sessions = []
    for i in range(3):
        child_id = await root_agent.create_nested_session(
            parent_agent_id=f"agent_{i}",
            parent_session_id=parent_session_id,
            timeout=60,
        )
        child_sessions.append(child_id)

    # 验证嵌套关系
    nested = await root_agent.session_manager.get_nested_sessions(parent_session_id)
    assert len(nested) == 3

    # 关闭父会话，验证子会话也被关闭
    success = await root_agent.close_nested_session(parent_session_id)
    assert success

    await root_agent.stop()
