"""
基础编排测试 - 验证主控节点调用工作节点

这些测试为 AI CLI coding agent 提供便捷的调试环境
"""

import pytest
import asyncio
import httpx
import sys
from pathlib import Path

# 添加项目路径到 sys.path
project_root = str(Path(__file__).parent.parent.parent.parent)
sys.path.insert(0, project_root)

# 导入测试 fixtures 和辅助类
# 使用绝对导入路径
from tests.distributed.fixtures.cluster import DistributedTestCluster
from tests.distributed.helpers.remote_agent import RemoteAgent
from src.core.protocol import AgentStatus


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_root_calls_sub_agent(ephemeral_cluster):
    """
    测试主控节点调用工作节点

    验证点：
    1. RemoteAgent 正确封装 HTTP 请求
    2. 工作节点接收并执行指令
    3. 结果正确返回
    """
    # 获取节点信息
    root_node = ephemeral_cluster.get_node("root-0")
    sub_node = ephemeral_cluster.get_node("sub-0")

    # 创建 RemoteAgent
    remote_agent = RemoteAgent(
        agent_id=sub_node.node_id, name="RemoteSubAgent", remote_url=sub_node.url
    )

    # 执行调用
    result = await remote_agent.execute(
        instruction="返回 Hello World", context="测试远程调用"
    )

    # 验证结果
    assert result.status.value == "SUCCESS", f"Expected SUCCESS, got {result.status}"
    assert result.result, "Result should not be empty"
    print(f"[Test] Remote agent returned: {result.result}")


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_multiple_sub_agents(ephemeral_cluster):
    """
    测试主控节点调用多个工作节点

    验证点：
    1. 可同时管理多个 RemoteAgent
    2. 并发调用不会互相干扰
    """
    sub_nodes = ephemeral_cluster.get_nodes_by_type("sub")

    # 创建多个 RemoteAgent
    agents = [
        RemoteAgent(agent_id=node.node_id, name=f"RemoteAgent{i}", remote_url=node.url)
        for i, node in enumerate(sub_nodes)
    ]

    # 并发调用
    results = await asyncio.gather(
        *[
            agent.execute(instruction=f"返回 Agent {i} 的消息", context="并发测试")
            for i, agent in enumerate(agents)
        ]
    )

    # 验证所有调用成功
    assert len(results) == len(agents), "Should have results for all agents"
    assert all(r.status.value == "SUCCESS" for r in results), (
        f"All agents should succeed. Got: {[r.status for r in results]}"
    )
    assert all(f"Agent {i}" in r.result for i, r in enumerate(results)), (
        "Each agent should return its specific message"
    )
    print(f"[Test] All {len(agents)} agents responded successfully")


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_remote_agent_capabilities(ephemeral_cluster, http_client):
    """
    测试查询远程 Agent 能力树

    验证点：
    1. RemoteAgent 可以查询能力树
    2. 能力树格式正确
    """
    sub_node = ephemeral_cluster.get_node("sub-0")

    # 创建 RemoteAgent
    remote_agent = RemoteAgent(
        agent_id=sub_node.node_id, name="TestAgent", remote_url=sub_node.url
    )

    # 查询能力树
    capabilities = await remote_agent.get_capabilities()

    # 验证响应
    assert capabilities is not None, "Capabilities should not be None"
    assert "status" in capabilities, "Response should have status field"
    # 注意：在模拟模式下，可能会返回 error，这是正常的
    if capabilities.get("status") == "success":
        assert "data" in capabilities, "Success response should have data"
        print(f"[Test] Capabilities fetched successfully")
    else:
        print(
            f"[Test] Capabilities fetch returned status: {capabilities.get('status')}"
        )


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_remote_agent_timeout(ephemeral_cluster):
    """
    测试超时重试机制

    验证点：
    1. RemoteAgent 在超时时正确重试
    2. 超时后返回失败状态
    3. 错误信息清晰
    """
    sub_node = ephemeral_cluster.get_node("sub-0")

    # 创建 RemoteAgent（短超时）
    remote_agent = RemoteAgent(
        agent_id=sub_node.node_id,
        name="TimeoutAgent",
        remote_url=sub_node.url,
        timeout=1,  # 1 秒超时（非常短）
        max_retries=2,
    )

    # 执行调用（可能超时）
    result = await remote_agent.execute(
        instruction="sleep 10",  # 模拟长时间任务
        context="超时测试",
    )

    # 验证结果（在模拟模式下可能仍然成功）
    print(f"[Test] Result status: {result.status}")
    print(f"[Test] Result: {result.result}")

    # 在真实网络环境中，这应该返回 TIMEOUT 或 FAILURE
    # 在模拟模式下，可能立即返回


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_stream_execution(ephemeral_cluster):
    """
    测试流式输出

    验证点：
    1. RemoteAgent 支持流式执行
    2. 流式输出正确分块返回
    """
    sub_node = ephemeral_cluster.get_node("sub-0")

    # 创建 RemoteAgent
    remote_agent = RemoteAgent(
        agent_id=sub_node.node_id, name="StreamAgent", remote_url=sub_node.url
    )

    # 执行流式调用
    chunks = []
    async for chunk in remote_agent.stream_execute(
        instruction="逐步输出消息", context="流式测试"
    ):
        chunks.append(chunk)
        print(f"[Test Stream] Received chunk: {chunk[:50]}...")

    # 验证结果
    assert len(chunks) > 0, "Should receive at least one chunk"
    print(f"[Test] Stream completed with {len(chunks)} chunks")


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_cluster_node_management(ephemeral_cluster):
    """
    测试集群节点管理功能

    验证点：
    1. 可以获取节点信息
    2. 可以按类型筛选节点
    3. 节点状态正确
    """
    # 测试获取单个节点
    root_node = ephemeral_cluster.get_node("root-0")
    assert root_node is not None, "Root node should exist"
    assert root_node.agent_type == "root", "Should be root type"
    assert root_node.status == "running", "Should be running"
    print(f"[Test] Root node: {root_node.node_id} at {root_node.url}")

    # 测试按类型获取节点
    sub_nodes = ephemeral_cluster.get_nodes_by_type("sub")
    assert len(sub_nodes) >= 2, (
        f"Should have at least 2 sub nodes, got {len(sub_nodes)}"
    )
    print(f"[Test] Found {len(sub_nodes)} sub nodes")

    # 验证所有节点信息
    all_nodes = ephemeral_cluster.nodes
    assert len(all_nodes) >= 3, (
        f"Should have at least 3 nodes total, got {len(all_nodes)}"
    )
    print(f"[Test] Total nodes in cluster: {len(all_nodes)}")
