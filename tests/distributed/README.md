# OneAgent 分布式测试框架

为 AI CLI coding agent（Claude Code、OpenCode）提供便捷的分布式测试环境。

## 📁 目录结构

```
OneAgent/
├── tests/distributed/
│   ├── conftest.py                    # pytest 全局配置和 fixtures
│   ├── fixtures/
│   │   ├── __init__.py
│   │   └── cluster.py                 # 集群管理 fixture
│   ├── helpers/
│   │   ├── __init__.py
│   │   └── remote_agent.py           # RemoteAgent 封装类
│   ├── scenarios/
│   │   └── test_basic_orchestration.py # 基础编排测试用例
│   └── scripts/
│       ├── start_cluster.sh             # 集群启动脚本
│       ├── stop_cluster.sh              # 集群停止脚本
│       └── run_distributed_tests.sh    # 测试运行脚本
├── infrastructure/
│   ├── Dockerfile.test                # 测试专用 Docker 镜像
│   └── docker-compose.test.yml         # Docker Compose 编排配置
└── logs/
    ├── test_failures/                  # 失败测试日志
    ├── test_runs/                      # 测试运行日志
    └── <date>.log                     # 每日运行日志
```

## 🚀 快速开始

### 方式 1：使用模拟模式（无需 Docker）

```bash
# 运行分布式测试（使用模拟集群）
./tests/distributed/scripts/run_distributed_tests.sh
```

### 方式 2：使用 Docker 集群

```bash
# 1. 启动 Docker 测试集群
./tests/distributed/scripts/start_cluster.sh

# 2. 运行测试
./tests/distributed/scripts/run_distributed_tests.sh USE_DOCKER=true

# 3. 停止集群
./tests/distributed/scripts/stop_cluster.sh
```

## 📊 核心组件

### 1. RemoteAgent（`helpers/remote_agent.py`）

**功能**：封装 HTTP 调用，使远程 OneAgent 表现为本地 Agent

**特性**：
- 统一的 `execute()` 和 `stream_execute()` 接口
- 自动重试机制（指数退避）
- SSE 流式输出支持
- 错误处理和状态返回

**使用示例**：
```python
from tests.distributed.helpers.remote_agent import RemoteAgent

remote_agent = RemoteAgent(
    agent_id="sub-0",
    name="RemoteSubAgent",
    remote_url="http://localhost:8001"
)

result = await remote_agent.execute(
    instruction="返回 Hello World",
    context="测试调用"
)

assert result.status.value == "SUCCESS"
```

### 2. 分布式测试集群（`fixtures/cluster.py`）

**功能**：管理多节点 OneAgent 集群

**特性**：
- 启动/停止容器（或模拟模式）
- 节点状态管理
- 网络故障注入（延迟、丢包）
- 日志收集和导出

**使用示例**：
```python
from tests.distributed.fixtures.cluster import DistributedTestCluster

cluster = DistributedTestCluster(use_docker=False)
await cluster.start_cluster(root_count=1, sub_count=3)

# 获取节点信息
root_node = cluster.get_node("root-0")
sub_nodes = cluster.get_nodes_by_type("sub")

# 注入网络故障
await cluster.inject_network_delay("sub-0", delay_ms=500)

# 停止节点
await cluster.stop_node("sub-0")
```

### 3. 测试场景（`scenarios/test_basic_orchestration.py`）

**现有测试**：
- `test_root_calls_sub_agent` - 基础远程调用测试
- `test_multiple_sub_agents` - 并发多节点调用
- `test_remote_agent_capabilities` - 能力树查询测试
- `test_remote_agent_timeout` - 超时重试测试
- `test_stream_execution` - 流式输出测试
- `test_cluster_node_management` - 集群管理测试

## 🔧 配置选项

### 环境变量

| 变量 | 默认值 | 说明 |
|-------|---------|------|
| `USE_DOCKER` | `false` | 是否使用 Docker 集群（false = 模拟模式） |
| `TEST_PATTERN` | `tests/distributed/` | 测试文件匹配模式 |
| `COVERAGE_ENABLED` | `true` | 是否生成覆盖率报告 |

### Docker 集群配置

编辑 `infrastructure/docker-compose.test.yml`：
- 修改服务数量（添加/删除 sub-N 服务）
- 调整端口映射
- 配置环境变量（AGENT_TYPE, PORT, LOG_LEVEL）

## 🧪 运行测试

### 运行所有分布式测试

```bash
# 模拟模式（推荐快速测试）
pytest tests/distributed/ -v -m distributed

# 使用 Docker 集群
USE_DOCKER=true pytest tests/distributed/ -v -m distributed
```

### 运行特定测试

```bash
# 基础编排测试
pytest tests/distributed/scenarios/test_basic_orchestration.py -v

# 特定测试
pytest tests/distributed/scenarios/test_basic_orchestration.py::test_root_calls_sub_agent -v
```

### 带覆盖率运行

```bash
pytest tests/distributed/ -v -m distributed --cov=src --cov-report=html
```

### 并行运行

```bash
# 使用 pytest-xdist
pytest tests/distributed/ -v -n auto --dist=loadscope
```

## 📝 测试标记

使用 pytest markers 进行选择性测试：

```bash
# 只运行分布式测试
pytest -m distributed

# 排除慢速测试
pytest -m "not slow"

# 只运行需要网络的测试
pytest -m network

# 只运行混沌测试
pytest -m chaos
```

## 🔍 调试和日志

### 查看测试失败日志

```bash
ls -l logs/test_failures/
cat logs/test_failures/failure_YYYYMMDD_HHMMSS.json
```

### 查看集群日志

```bash
ls -l .OneAgent/cluster_logs/
cat .OneAgent/cluster_logs/cluster_logs_YYYYMMDD_HHMMSS.json
```

### 查看每日运行日志

```bash
ls -l logs/
tail -f logs/$(date +%Y-%m-%d).log
```

### 使用调试器

```bash
# 在失败时进入 pdb
pytest tests/distributed/ -v -m distributed --pdb

# 在第一个失败时停止
pytest tests/distributed/ -v -m distributed -x
```

## 🐳 Docker 集群管理

### 启动集群

```bash
./tests/distributed/scripts/start_cluster.sh
```

这会启动：
- 1 个主控节点（RootOneAgent）- 端口 8000
- 3 个工作节点（SubOneAgent）- 端口 8001-8003

### 停止集群

```bash
./tests/distributed/scripts/stop_cluster.sh
```

这会：
- 停止所有容器
- 收集容器日志
- 清理旧日志文件

### 查看容器状态

```bash
docker ps --filter "name=oneagent-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
```

### 查看容器日志

```bash
# 实时查看日志
docker logs -f oneagent-root-0

# 查看最近 100 行
docker logs --tail 100 oneagent-sub-0
```

## 📊 测试覆盖率

生成覆盖率报告：

```bash
pytest tests/distributed/ -v --cov=src --cov-report=html
```

打开报告：
```bash
# macOS
open htmlcov/index.html

# Linux
xdg-open htmlcov/index.html
```

## ⚠️ 常见问题

### Q: 测试失败，提示 "pytest 未安装"

**A**: 安装测试依赖：
```bash
pip install pytest pytest-asyncio pytest-cov httpx
```

### Q: Docker 容器启动失败

**A**: 检查：
1. Docker 是否运行：`docker info`
2. 端口是否被占用：`lsof -i :8000`
3. 查看 Docker 日志：`docker logs oneagent-root-0`

### Q: 测试超时

**A**:
1. 使用模拟模式（`USE_DOCKER=false`）
2. 增加测试超时：`pytest tests/distributed/ -v --timeout=300`
3. 调整 RemoteAgent 的 `timeout` 参数

### Q: 网络错误 "Connection refused"

**A**:
1. 确认集群已启动：`docker ps`
2. 检查健康检查：`curl http://localhost:8000/health`
3. 等待节点就绪（脚本会自动等待）

## 🔧 为 AI CLI Coding Agent 优化

### 快速测试流程

```bash
# 1. 一条命令运行测试
./tests/distributed/scripts/run_distributed_tests.sh

# 2. 查看结果
# ✓ 所有测试通过
# 覆盖率报告: htmlcov/index.html
```

### 调试友好的特性

1. **清晰的错误信息**
   - 测试失败时自动保存日志
   - 详细的断言错误消息
   - 彩色输出（成功/失败/警告）

2. **状态快照**
   ```bash
   # 断点调试
   pytest tests/distributed/scenarios/test_basic_orchestration.py::test_root_calls_sub_agent -k "test_root" --pdb
   ```

3. **并发测试加速**
   ```bash
   # 使用 pytest-xdist 并行运行
   pytest tests/distributed/ -v -n auto --dist=loadscope
   ```

## 📚 扩展测试场景

### 添加新的测试用例

在 `tests/distributed/scenarios/` 下创建新文件：

```python
"""
新的测试场景
"""

import pytest
import asyncio
from tests.distributed.fixtures.cluster import DistributedTestCluster
from tests.distributed.helpers.remote_agent import RemoteAgent


@pytest.mark.distributed
@pytest.mark.asyncio
async def test_your_new_test(ephemeral_cluster):
    """测试描述"""
    # 你的测试逻辑
    pass
```

### 添加故障注入测试

```python
@pytest.mark.distributed
@pytest.mark.chaos
@pytest.mark.asyncio
async def test_network_failure(ephemeral_cluster):
    """测试网络分区故障"""
    # 1. 注入网络故障
    await ephemeral_cluster.inject_network_loss("sub-0", loss_percent=100)

    # 2. 验证降级行为
    # ...

    # 3. 恢复网络
    # ...
```

## ✅ 验收标准

完成以下检查即表示测试框架可用：

- [ ] `./tests/distributed/scripts/run_distributed_tests.sh` 执行成功
- [ ] 所有标记为 `@pytest.mark.distributed` 的测试通过
- [ ] 日志正确生成到 `logs/` 目录
- [ ] `RemoteAgent` 可以成功调用远程节点
- [ ] 集群管理 fixture 正常工作
- [ ] Docker 集群可以启动/停止（如果使用 Docker）

## 📞 联系和支持

如遇问题，请检查：
1. 测试日志：`logs/test_failures/`
2. 集群日志：`.OneAgent/cluster_logs/`
3. 容器状态：`docker ps`

或提供以下信息寻求帮助：
- OS 和版本
- Python 版本
- Docker 版本（如果使用）
- 完整的错误输出
