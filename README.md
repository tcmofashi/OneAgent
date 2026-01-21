# OneAgent

**多代理协作框架 / Multi-Agent Orchestration Framework**

OneAgent 是一个支持多模型、多代理协作的智能编排框架，支持 Windows/macOS/Linux 平台。

## 项目架构

```
OneAgent/
├── main.py                     # 主入口（CLI 模式）
├── config/
│   └── config.toml             # 全局配置文件
├── src/
│   ├── core/                   # 核心框架
│   │   ├── orchestrator.py     # 主控编排器 (ReAct Loop)
│   │   ├── react_agent.py      # 通用 ReAct Agent 基类
│   │   ├── capability.py       # Agent/Tool 基类定义
│   │   ├── registry.py         # 全局能力注册表
│   │   ├── llm.py              # LLM 客户端封装
│   │   ├── config.py           # 配置加载器
│   │   └── session.py          # 会话管理
│   ├── capabilities/
│   │   ├── agents/             # 子代理实现
│   │   │   ├── qwen_agent/     # Qwen Code CLI 桥接代理
│   │   │   ├── web_agent/      # Playwright 网页浏览代理
│   │   │   ├── autoglm_gui_agent/ # AutoGLM 手机自动化代理
│   │   │   └── hello_world_agent/ # 示例代理
│   │   └── tools/              # 全局共享工具
│   ├── server/                 # Web 服务器 & MCP 服务
│   └── utils/                  # 工具类
├── requirements.txt            # Python 依赖
└── tests/                      # 测试用例
```

---

## 部署方式

### 方式一：CLI 模式（命令行交互）

最简单的运行方式，直接通过命令行与 Agent 交互。

```bash
# 1. 克隆项目
git clone <repo-url>
cd OneAgent

# 2. 创建虚拟环境
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置 API Keys
# 编辑 config/config.toml，填入你的 API Keys

# 5. 运行
python main.py
```

**单次命令执行**：
```bash
python main.py "帮我创建一个 hello.txt 文件"
```

### 方式二：Web 服务器模式

提供 HTTP API 和 Web UI 界面。

```bash
# 启动 Web 服务器
uvicorn src.server.web_server:app --host 0.0.0.0 --port 8000

# 或使用 uv（推荐）
uv run uvicorn src.server.web_server:app --host 0.0.0.0 --port 8000
```

访问 `http://localhost:8000` 使用 Web 界面。

### 方式三：MCP 服务器模式

作为 MCP (Model Context Protocol) 服务器运行，供其他 AI 助手（如 Claude Code）调用。

详见 [CLAUDE.md](./CLAUDE.md) 了解 MCP 集成说明。

---

## 依赖说明

### Python 依赖 (requirements.txt)

| 包名 | 用途 | 必需 |
|------|------|------|
| `openai>=1.0.0` | OpenAI 兼容 API 客户端 | ✅ |
| `toml` | 配置文件解析 | ✅ |
| `pydantic` | 数据模型验证 | ✅ |
| `colorama` | 终端彩色输出 | ✅ |
| `mcp` | Model Context Protocol | ✅ |
| `fastapi` | Web 服务器框架 | ✅ |
| `uvicorn` | ASGI 服务器 | ✅ |
| `sse-starlette` | Server-Sent Events 支持 | ✅ |
| `python-multipart` | 文件上传支持 | ✅ |
| `megfile` | 文件操作（GUI Agent 用） | ⚠️ 可选 |
| `pyyaml` | YAML 解析 | ⚠️ 可选 |
| `Pillow` | 图像处理 | ⚠️ 可选 |
| `jsonlines` | JSONL 格式支持 | ⚠️ 可选 |
| `fastmcp` | Fast MCP 实现 | ⚠️ 可选 |
| `playwright` | 网页自动化（Web Agent 用） | ⚠️ 可选 |
| `trafilatura` | 网页内容提取 | ⚠️ 可选 |

### 额外依赖

#### Playwright 浏览器驱动

如果使用 `web_agent`，需要安装 Playwright 浏览器：

```bash
# 安装 Playwright 浏览器驱动
playwright install
# 或仅安装 Chromium
playwright install chromium
```

#### Node.js (Qwen Agent)

如果使用 `qwen_bridge_agent`，需要安装 Node.js：

- **Windows**: 从 https://nodejs.org/ 下载安装
- **macOS**: `brew install node`
- **Linux**: `sudo apt install nodejs npm`

---

## 配置说明

### LLM 模型配置 (config/config.toml)

```toml
[llm]
active_model_label = "v3-2"  # 默认使用的模型

[llm.functional_roles]
compressor = "v3-2"          # 上下文压缩
orchestrator = "glm"         # 主编排器
code_generation = "v3-2"     # 代码生成
json_cleaner = "qwen-flash"  # JSON 修复
web_browsing = "v3-2"        # 网页浏览

[llm.providers.siliconflow]
api_base = "https://api.siliconflow.cn/v1"
api_key = "your-api-key"

[llm.models]
v3-2 = { provider = "siliconflow", model_name = "Pro/deepseek-ai/DeepSeek-V3.2" }
```

### Agent 加载配置

```toml
[capabilities]
mode = "blacklist"           # all / whitelist / blacklist
blacklist = ["gelab_gui_agent"]  # 排除的 Agent

[capabilities.mcp]
enabled = true               # 是否加载 MCP 服务
```

---

## 可用代理 (Agents)

| Agent 名称 | 描述 | 依赖 |
|-----------|------|------|
| `qwen_bridge_agent` | Qwen Code CLI 桥接，强大的编程代理 | Node.js |
| `web_agent` | Playwright 网页浏览代理 | playwright |
| `autoglm_gui_agent` | AutoGLM 手机 GUI 自动化 | adb/hdc |
| `hello_world_agent` | 示例代理（仅打招呼） | 无 |

---

## 分布式测试框架

OneAgent 提供了完整的分布式测试框架，用于 AI CLI coding agent（Claude Code、OpenCode）调试多机器部署。

### 快速开始（模拟模式）

最简单的测试方式，无需 Docker：

```bash
# 运行分布式测试（模拟模式）
pytest tests/distributed/ -v -m distributed

# 查看结果
# ✓ 4/6 测试通过
# ✓ 64 个现有测试全部通过（无回归）
```

### 使用 Docker 集群

用于真实的分布式场景测试：

```bash
# 1. 安装 Docker 依赖
pip install docker

# 2. 启动测试集群（1 root + 3 sub 节点）
./tests/distributed/scripts/start_cluster.sh

# 3. 运行测试
pytest tests/distributed/ -v -m distributed

# 4. 停止集群并收集日志
./tests/distributed/scripts/stop_cluster.sh
```

### 测试场景

| 测试用例 | 说明 | 状态 |
|---------|------|------|
| `test_root_calls_sub_agent` | 主控节点调用工作节点 | ✅ 框架完成 |
| `test_multiple_sub_agents` | 并发调用多个工作节点 | ✅ 框架完成 |
| `test_remote_agent_capabilities` | 查询远程 Agent 能力树 | ✅ 通过 |
| `test_remote_agent_timeout` | 超时重试机制测试 | ✅ 通过 |
| `test_stream_execution` | 流式输出测试 | ✅ 通过 |
| `test_cluster_node_management` | 集群节点管理测试 | ✅ 通过 |

### 核心组件

#### 1. RemoteAgent

封装 HTTP 调用到远程 OneAgent 实例，提供统一接口：

```python
from tests.distributed.helpers.remote_agent import RemoteAgent

remote_agent = RemoteAgent(
    agent_id="sub-0",
    name="RemoteSubAgent",
    remote_url="http://localhost:8001"
)

# 非流式调用
result = await remote_agent.execute(
    instruction="返回 Hello World",
    context="测试调用"
)

# 流式调用
async for chunk in remote_agent.stream_execute(
    instruction="逐步输出消息",
    context="流式测试"
):
    print(chunk)
```

#### 2. 分布式测试集群

管理多节点 OneAgent 集群，支持双模式：

```python
from tests.distributed.fixtures.cluster import DistributedTestCluster

# 创建集群（模拟模式）
cluster = DistributedTestCluster(use_docker=False)
await cluster.start_cluster(root_count=1, sub_count=3)

# 获取节点
root_node = cluster.get_node("root-0")
sub_nodes = cluster.get_nodes_by_type("sub")

# 故障注入（混沌工程）
await cluster.inject_network_delay("sub-0", delay_ms=500)
await cluster.inject_network_loss("sub-1", loss_percent=50)

# 清理
await cluster.shutdown()
```

#### 3. Pytest Fixtures

预定义的测试夹件：

| Fixture | 作用 | 作用域 |
|---------|------|---------|
| `ephemeral_cluster` | 每个测试独立的集群 | 测试级 |
| `distributed_cluster` | 跨测试共享的集群 | 会话级 |
| `http_client` | HTTP 客户端 | 测试级 |

```python
import pytest

@pytest.mark.distributed
@pytest.mark.asyncio
async def test_my_scenario(ephemeral_cluster):
    sub_node = ephemeral_cluster.get_node("sub-0")
    # 测试逻辑
```

### Docker 集群管理

查看集群状态：

```bash
# 查看容器状态
docker ps --filter "name=oneagent-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 查看容器日志
docker logs -f oneagent-root-0
docker logs --tail 100 oneagent-sub-0
```

### 测试标记

选择性运行测试：

```bash
# 只运行分布式测试
pytest -m distributed

# 排除慢速测试
pytest -m "not slow"

# 只运行混沌测试
pytest -m chaos

# 只运行需要网络的测试
pytest -m network
```

### 覆盖率报告

生成测试覆盖率报告：

```bash
# 生成 HTML 覆盖率报告
pytest tests/distributed/ --cov=src --cov-report=html

# 查看报告
# macOS: open htmlcov/index.html
# Linux: xdg-open htmlcov/index.html
```

### 日志和调试

查看测试失败日志：

```bash
# 查看失败测试日志
ls -l logs/test_failures/
cat logs/test_failures/failure_YYYYMMDD_HHMMSS.json

# 查看集群日志
ls -l .OneAgent/cluster_logs/
cat .OneAgent/cluster_logs/cluster_logs_YYYYMMDD_HHMMSS.json
```

### 依赖要求

| 包名 | 用途 | 必需 |
|------|------|------|
| `pytest` | 测试框架 | ✅ |
| `pytest-asyncio` | 异步测试支持 | ✅ |
| `pytest-cov` | 覆盖率报告 | ✅ |
| `httpx` | HTTP 客户端 | ✅ |
| `docker` | Docker API（可选） | ❌ |

### 文档

完整的测试框架文档：

- [分布式测试 README](./tests/distributed/README.md) - 详细使用指南
- [验证报告](./tests/distributed/VERIFICATION_REPORT.md) - 验证结果和证据

---

## 快速开始示例

```bash
# 启动交互式 CLI
python main.py

# 提示词示例
User: 帮我搜索一下今天的新闻
User: 创建一个 Python 脚本计算斐波那契数列
User: 打开百度搜索 "深度学习"
```

---

## License

MIT License

