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

