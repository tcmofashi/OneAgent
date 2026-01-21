"""
分布式测试全局配置和 Fixtures

为 AI CLI coding agent 提供便捷的测试环境配置
"""

import pytest
import pytest_asyncio
import asyncio
import sys
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass
import httpx


# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


# ============================================================================
# 数据类定义
# ============================================================================


@dataclass
class AgentNode:
    """Agent 节点信息"""

    node_id: str
    agent_type: str  # "root" or "sub"
    port: int
    container_id: str
    url: str
    status: str = "running"


class DistributedTestCluster:
    """
    分布式测试集群管理器

    功能：
    - 启动多个 OneAgent Docker 容器
    - 管理容器生命周期
    - 提供集群信息查询
    - 注入网络故障
    """

    def __init__(self, use_docker=False):
        """
        初始化集群管理器

        Args:
            use_docker: 是否使用 Docker（False = 使用模拟模式）
        """
        self.use_docker = use_docker
        self.docker_client = None
        self.nodes: Dict[str, AgentNode] = {}
        self.started = False

        if use_docker:
            try:
                import docker

                self.docker_client = docker.from_env()
            except ImportError:
                print("Warning: docker-py not installed, using simulated mode")
                self.use_docker = False

    async def start_cluster(
        self, root_count: int = 1, sub_count: int = 3, base_port: int = 8000
    ):
        """
        启动测试集群

        Args:
            root_count: 主控节点数量
            sub_count: 工作节点数量
            base_port: 起始端口号
        """
        if self.use_docker:
            self._start_docker_cluster(root_count, sub_count, base_port)
        else:
            self._start_simulated_cluster(root_count, sub_count, base_port)

        # 等待所有节点就绪
        await self._wait_for_ready()
        self.started = True

    def _start_docker_cluster(self, root_count: int, sub_count: int, base_port: int):
        """启动 Docker 容器集群"""
        # 启动主控节点
        for i in range(root_count):
            node_id = f"root-{i}"
            port = base_port + i
            # 这里需要实际的 Dockerfile
            # 暂时使用模拟实现
            print(
                f"[Cluster] Would start Docker container for {node_id} on port {port}"
            )

        # 启动工作节点
        for i in range(sub_count):
            node_id = f"sub-{i}"
            port = base_port + root_count + i
            print(
                f"[Cluster] Would start Docker container for {node_id} on port {port}"
            )

    def _start_simulated_cluster(self, root_count: int, sub_count: int, base_port: int):
        """启动模拟集群（无 Docker）"""
        # 启动主控节点
        for i in range(root_count):
            node_id = f"root-{i}"
            port = base_port + i
            self.nodes[node_id] = AgentNode(
                node_id=node_id,
                agent_type="root",
                port=port,
                container_id=f"simulated-{node_id}",
                url=f"http://localhost:{port}",
                status="running",
            )
            print(f"[Cluster] Started simulated node {node_id} on port {port}")

        # 启动工作节点
        for i in range(sub_count):
            node_id = f"sub-{i}"
            port = base_port + root_count + i
            self.nodes[node_id] = AgentNode(
                node_id=node_id,
                agent_type="sub",
                port=port,
                container_id=f"simulated-{node_id}",
                url=f"http://localhost:{port}",
                status="running",
            )
            print(f"[Cluster] Started simulated node {node_id} on port {port}")

    async def _wait_for_ready(self, timeout: int = 30):
        """等待所有节点就绪"""
        async with httpx.AsyncClient(timeout=2.0) as client:
            start = asyncio.get_event_loop().time()

            while True:
                all_ready = True
                for node in self.nodes.values():
                    # 在模拟模式下，跳过实际健康检查
                    if self.use_docker:
                        try:
                            response = await client.get(f"{node.url}/health", timeout=1)
                            if response.status_code != 200:
                                all_ready = False
                                break
                        except:
                            all_ready = False
                            break

                if all_ready:
                    print(f"[Cluster] All {len(self.nodes)} nodes ready")
                    break

                if asyncio.get_event_loop().time() - start > timeout:
                    print(f"[Cluster] Warning: Startup timeout, proceeding anyway")
                    break

                await asyncio.sleep(1)

    def get_node(self, node_id: str) -> Optional[AgentNode]:
        """获取节点信息"""
        return self.nodes.get(node_id)

    def get_nodes_by_type(self, agent_type: str) -> List[AgentNode]:
        """按类型获取节点列表"""
        return [n for n in self.nodes.values() if n.agent_type == agent_type]

    async def inject_network_delay(self, node_id: str, delay_ms: int):
        """
        注入网络延迟

        Args:
            node_id: 节点 ID
            delay_ms: 延迟毫秒数
        """
        if self.use_docker:
            print(f"[Cluster] Would inject {delay_ms}ms delay to {node_id}")
        else:
            print(f"[Cluster] Simulated: {delay_ms}ms delay injected to {node_id}")

    async def inject_network_loss(self, node_id: str, loss_percent: int):
        """
        注入网络丢包

        Args:
            node_id: 节点 ID
            loss_percent: 丢包百分比
        """
        if self.use_docker:
            print(f"[Cluster] Would inject {loss_percent}% loss to {node_id}")
        else:
            print(f"[Cluster] Simulated: {loss_percent}% loss injected to {node_id}")

    async def stop_node(self, node_id: str):
        """停止单个节点"""
        node = self.nodes.get(node_id)
        if node:
            if self.use_docker:
                print(f"[Cluster] Would stop Docker container {node.container_id}")
            else:
                print(f"[Cluster] Stopped simulated node {node_id}")
            node.status = "stopped"

    async def start_node(self, node_id: str):
        """启动已停止的节点"""
        node = self.nodes.get(node_id)
        if node and node.status == "stopped":
            if self.use_docker:
                print(f"[Cluster] Would start Docker container {node.container_id}")
            else:
                print(f"[Cluster] Started simulated node {node_id}")
            node.status = "running"
            await self._wait_for_ready()

    async def shutdown(self):
        """关闭集群"""
        if self.use_docker:
            print(f"[Cluster] Would stop {len(self.nodes)} Docker containers")
        else:
            print(f"[Cluster] Stopping {len(self.nodes)} simulated nodes")
        self.nodes.clear()
        self.started = False

    def collect_logs(self, node_id: str) -> str:
        """
        收集节点日志

        Args:
            node_id: 节点 ID

        Returns:
            日志文本
        """
        node = self.nodes.get(node_id)
        if not node:
            return ""

        if self.use_docker:
            return f"[Cluster] Would collect logs from {node.container_id}"
        else:
            return f"[Cluster] Simulated logs from {node_id}"


# ============================================================================
# Pytest Fixtures
# ============================================================================


def pytest_configure(config):
    """pytest 配置钩子"""
    config.addinivalue_line(
        "markers", "distributed: 标记分布式测试（需要 Docker 环境）"
    )
    config.addinivalue_line("markers", "slow: 慢速测试（多节点、长耗时）")
    config.addinivalue_line("markers", "chaos: 混沌测试（故障注入）")
    config.addinivalue_line("markers", "network: 测试需要网络访问")


@pytest.fixture(scope="session")
def event_loop():
    """会话级事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def distributed_cluster():
    """
    会话级分布式集群 Fixture

    适用于需要在多个测试间共享集群的场景
    """
    cluster = DistributedTestCluster(use_docker=False)  # 默认使用模拟模式
    await cluster.start_cluster(root_count=1, sub_count=3)
    yield cluster
    await cluster.shutdown()


@pytest_asyncio.fixture
async def ephemeral_cluster():
    """
    测试级分布式集群 Fixture

    每个测试都创建新的集群（隔离性更好）
    """
    cluster = DistributedTestCluster(use_docker=False)
    await cluster.start_cluster(root_count=1, sub_count=2)
    yield cluster
    await cluster.shutdown()


@pytest.fixture
def cluster_logs(distributed_cluster):
    """
    收集集群日志 Fixture

    用于测试失败时诊断
    """
    yield

    # 测试结束后自动收集日志
    logs = {}
    for node_id in distributed_cluster.nodes:
        logs[node_id] = distributed_cluster.collect_logs(node_id)

    # 保存到文件
    import json
    from datetime import datetime

    log_dir = Path(".OneAgent/cluster_logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"cluster_logs_{timestamp}.json"
    log_file.write_text(json.dumps(logs, indent=2), encoding="utf-8")


@pytest_asyncio.fixture
async def http_client():
    """HTTP 客户端 fixture"""
    import httpx

    async with httpx.AsyncClient(timeout=30.0) as client:
        yield client


@pytest.fixture
async def mock_orchestrator():
    """Mock Orchestrator fixture"""
    from src.core.orchestrator import Orchestrator

    orchestrator = Orchestrator()
    yield orchestrator


# ============================================================================
# 自动收集日志
# ============================================================================


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """
    测试报告钩子：自动收集失败测试的日志
    """
    outcome = yield
    report = outcome.get_result()

    if report.when == "call" and report.failed:
        # 收集相关信息
        test_name = item.nodeid
        failure_info = {
            "test": test_name,
            "outcome": report.outcome,
            "longrepr": str(report.longrepr) if report.longrepr else None,
        }

        # 保存到文件
        import json
        from datetime import datetime

        log_dir = Path("logs/test_failures")
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"failure_{timestamp}.json"
        log_file.write_text(json.dumps(failure_info, indent=2), encoding="utf-8")

        print(f"\n[pytest] Failure log saved to: {log_file}")
