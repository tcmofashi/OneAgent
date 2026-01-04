# OneAgent

一个本地多 Agent 协作系统，基于 ReAct 架构的 Orchestrator 负责任务规划和调度，支持多种子 Agent（代码编辑、网页浏览、手机 GUI 控制等）。

## 特性

- 🧠 **ReAct 架构的主控 Agent** - 智能任务规划、分解和调度
- 🔧 **多种子 Agent 支持**
  - `qwen_bridge_agent` - 代码编辑、命令行执行、Web 搜索
  - `web_agent` - 网页浏览、表单填写、截图
  - `autoglm_gui_agent` - 手机 GUI 自动化（Android/iOS/鸿蒙）
- 📝 **持久化任务列表** - 跟踪任务进度
- 🔄 **流式输出** - 实时显示思考过程和执行结果
- 🔌 **MCP 协议支持** - 可扩展的工具集成

## 快速开始

### 1. 安装依赖

```bash
cd OneAgent
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或 .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 2. 配置

复制配置模板并填入 API 密钥：

```bash
cp config/config.template.toml config/config.toml
```

编辑 `config/config.toml`：

```toml
[core]
workspace = "./workspace"
language = "zh"  # 或 "en"

[llm]
active_provider = "siliconflow"
active_model_label = "deepseek-v3"

[llm.providers.siliconflow]
api_base = "https://api.siliconflow.cn/v1"
api_key = "YOUR_API_KEY_HERE"  # 替换为你的 API 密钥

[llm.models]
deepseek-v3 = { provider = "siliconflow", model_name = "deepseek-ai/DeepSeek-V3" }
```

### 3. 运行

#### 交互模式

```bash
python main.py
```

#### 单次命令模式

```bash
python main.py "帮我查看一下现在系统的内存使用率"
```

## 使用示例

### 系统信息查询

```bash
python main.py "查看系统内存和磁盘使用情况"
```

### 代码编辑任务

```bash
python main.py "帮我在 src/utils/ 目录下创建一个 helper.py 文件，实现一个简单的日志工具"
```

### 网页浏览任务

```bash
python main.py "帮我打开 GitHub 并搜索 OneAgent 相关项目"
```

## 项目结构

```
OneAgent/
├── main.py                 # 程序入口
├── config/
│   ├── config.template.toml  # 配置模板
│   └── config.toml           # 实际配置 (gitignored)
├── src/
│   ├── core/
│   │   ├── orchestrator.py   # 主控 Agent (ReAct 循环)
│   │   ├── react_agent.py    # ReAct Agent 基类
│   │   ├── capability.py     # 能力基类定义
│   │   ├── registry.py       # 能力注册表
│   │   ├── compressor.py     # 上下文压缩器
│   │   ├── config.py         # 配置管理
│   │   └── templates.py      # Prompt 模板
│   ├── capabilities/
│   │   ├── agents/           # 子 Agent 目录
│   │   │   ├── qwen_agent/   # Qwen Code CLI Agent
│   │   │   ├── web_agent/    # 网页浏览 Agent
│   │   │   └── autoglm_gui_agent/  # 手机 GUI Agent
│   │   └── tools/            # 全局工具
│   ├── runtime_tools/        # 子 Agent 专用工具
│   └── utils/
│       └── loader.py         # 能力加载器
├── logs/                     # 日志和会话数据
└── tests/                    # 测试文件
```

## 配置说明

### 模型配置

在 `config.toml` 中配置 LLM 提供商和模型：

```toml
[llm]
active_provider = "siliconflow"
active_model_label = "deepseek-v3"

# 可选：为不同功能指定不同模型
[llm.functional_roles]
code_generation = "qwen-coder"     # 代码生成专用模型
context_compression = "v3-2"       # 上下文压缩专用模型

[llm.models]
deepseek-v3 = { provider = "siliconflow", model_name = "deepseek-ai/DeepSeek-V3" }
qwen-coder = { provider = "siliconflow", model_name = "Qwen/Qwen2.5-Coder-32B-Instruct" }
```

### Agent 过滤

控制加载哪些 Agent：

```toml
[capabilities]
mode = "blacklist"  # "all", "whitelist", "blacklist"
blacklist = ["gelab_gui_agent"]  # 排除的 Agent
# whitelist = ["qwen_agent", "web_agent"]  # 仅加载这些 Agent
```

## 子 Agent 能力

| Agent               | 能力                                                             | 工具                                   |
| ------------------- | ---------------------------------------------------------------- | -------------------------------------- |
| `qwen_bridge_agent` | 代码编辑, 命令行执行(bash/git/npm/pip/docker), Web搜索, 文件操作 | report_status                          |
| `web_agent`         | 网页导航, 元素点击, 表单填写, 内容读取, 截图, JS执行             | click, fill, navigate, screenshot, ... |
| `autoglm_gui_agent` | 手机GUI控制(点击/输入/滑动), 应用启动切换, 多平台支持            | report_status                          |

## 开发

### 添加新的子 Agent

1. 在 `src/capabilities/agents/` 下创建目录
2. 创建 `agent.py` 继承 `ReactAgent` 或 `BaseAgent`
3. 可选：在 `tools/` 子目录添加专属工具
4. 可选：创建 `mcp.toml` 配置 MCP 服务器

示例：

```python
from src.core.react_agent import ReactAgent

class MyAgent(ReactAgent):
    name = "my_agent"
    description = "我的自定义 Agent"
    allowed_tools = ["report_status"]
    
    CAPABILITIES_SUMMARY = "能力1, 能力2, 能力3"
    
    def get_context_description(self) -> str:
        return f"{self.name} (Agent): 描述 [{self.CAPABILITIES_SUMMARY}] [Tools: {', '.join(self.allowed_tools)}]"
```

### 运行测试

```bash
python -m pytest tests/ -v
```

## 许可证

见 [LICENSE_DEPENDENCIES.md](LICENSE_DEPENDENCIES.md)
