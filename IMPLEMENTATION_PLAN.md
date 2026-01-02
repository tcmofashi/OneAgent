# 项目架构计划：本地多 Agent 协作系统 (v2)

## 目标描述
创建一个运行在单机环境下的 Python 项目，核心是一个基于 **ReAct 架构** 的 Orchestrator Agent。它负责维护任务列表，分析用户意图，并通过调用不同类型的工具（子 Agent、本地函数、MCP 服务器）来完成复杂的任务。

## 核心架构设计

### 1. 核心组件
*   **Orchestrator (主控 Agent)**:
    *   **架构**: **ReAct (Reasoning + Acting)**。
    *   **核心职责**:
        1.  **任务规划**: 在对话开始时生成任务列表 (Task List)。
        2.  **状态管理**: 维护一个**持久化的文本区域 (Persistent Task List)**，作为 Prompt 的一部分注入上下文。
        3.  **调度执行**: ReAct 循环中，Agent 可以调用 `update_task_list` 工具来更新这个区域的状态。
    *   **实现**: 基于 Python `asyncio` 和 `AsyncOpenAI` SDK。
    *   **关键特性**: Strict "Task List" injection in every turn.
    *   **Unified Registry (统一注册中心)**:
    *   **能够注册三种类型的 Capabilities**:
        1.  **Directory-Based Python Agents**: 每个 Agent 拥有独立的子目录，包含 `agent.py` (继承 BaseAgent)、`tools/` (私有工具) 和 `mcp.toml` (私有 MCP 配置)。
        2.  **Orchestrator Capabilities (Root Scope)**: 位于 `src/capabilities/` 根目录下的 `tools/` 和 `mcp.toml`。
            *   **所有权**: 仅属于最上层 Agent (Orchestrator)。
            *   **可见性**: 子 Agent 可见但不拥有 (Read-Only Meta)。
            *   **调用方式**: 子 Agent 必须通过 `INTERRUPTED` 状态向上申请调用。
*   **Context Compressor (上下文压缩器)**:
    *   **职责**: 在 Agent 层级调用时，负责提炼上级 Agent 的冗长上下文。
    *   **增强特性**: 注入 "Upstream Capabilities" (上级能力清单)。子 Agent 可以看到这些工具，但无法直接调用。
    *   **输出**: "Core Request" + "Compressed Context" + "Upstream Tool List".
*   **Configuration Manager (配置管理)**:
    *   **格式**: TOML。
    *   **结构**: 
        *   区分 `config.template.toml` 和实际 `config.toml`。
        *   `[core]`: 基础路径配置。
        *   `[agent]`: 身份标识 (Name, ID)，用于分布式网络识别。
        *   `[llm]`: 供应商 (Providers)、模型定义 (Models)、功能映射 (Functional Roles)。
        *   **模型配置策略**: 
            *   定义 `Providers` (如 SiliconFlow, OpenAI, Deepseek)。
            *   定义 `Models` (具体的模型标识)。
            *   通过更改配置中的 `active_model_label` 快速切换同一 Provider 下的不同模型。

### 2. 交互协议 (Protocols)
#### Hierarchical Dispatch (层级分发)
*   **Orchestrator -> Agent**: 
    1.  提取当前状态。
    2.  调用 `Compressor` 生成精简指令。
    3.  下发指令给子 Agent。
#### Reporting & Escalation (上报与拒绝)
*   **Agent -> Orchestrator**: 必须返回标准化的 `ExecutionResult`。
    *   **Status Types**:
        *   `SUCCESS`: 任务完成。
        *   `FAILURE`: 执行失败 (客观原因)。
        *   `REJECTED`: 拒绝执行 (任务不合理/超出范围)，导致任务直接取消。
        *   `INTERRUPTED`: 请求中断 (需上级协助/挂起)，主控处理完请求后，将结果作为 Context 注入并再次调度该 Agent 继续执行。
    *   **Escalation Mechanism**: 当子 Agent 需要使用上级能力时，使用 `INTERRUPTED` 状态，并在 Summary 中指明需求。Orchestrator 执行后再次 invoke 该 Agent。收到 REJECTED 后，必须重新进行任务匹配 (Re-route)，而不能简单重试。

### 3. 工作流 (Workflow)
1.  **初始化**: 
    *   加载 `config/config.toml`。
    *   **Registry** 扫描并加载本地 Tools、Code Agents，连接配置的 MCP Servers。
2.  **用户输入**: 用户输入自然语言指令。
3.  **Orchestrator 规划 (ReAct 循环)**:
    *   **Thought**: 分析用户需求，生成初始 **Task List**。
    *   **Action**: 选择当前任务，决定调用哪个 Capability (Agent/Tool/MCP)。
    *   **Observation**: 获取工具执行结果。
    *   **Update**: 更新 Task List 状态 (Pending -> Done)。
    *   **Loop**: 重复上述过程，直到 Task List 全部完成。
4.  **最终响应 (Final Answer)**: 汇总结果向用户汇报。

### 4. 配置结构示例 (TOML)
```toml
[core]
workspace = "./workspace"

[llm]
active_provider = "siliconflow"
active_model = "deepseek-v3" # 切换模型只需改这里

[llm.providers.siliconflow]
api_base = "https://api.siliconflow.cn/v1"
api_key = "sk-..."

[llm.providers.openai]
api_base = "https://api.openai.com/v1"
api_key = "sk-..."

[llm.models]
deepseek-v3 = { provider = "siliconflow", model_name = "deepseek-ai/DeepSeek-V3" }
gpt-4o = { provider = "openai", model_name = "gpt-4o" }
```

## 目录结构规划
```
OneAgent/
├── main.py                 # 程序入口
├── requirements.txt
├── config/                 # 配置目录
│   ├── config.template.toml
│   ├── config.toml (gitignored)
├── src/
│   ├── __init__.py
│   ├── core/
│   │   ├── orchestrator.py # ReAct 循环，Task List 管理
│   │   ├── llm.py          # AsyncOpenAI 封装
│   │   ├── config.py       # TOML 配置加载逻辑
│   │   ├── registry.py     # 统一注册 Agents, Tools, MCP
│   │   ├── compressor.py   # Context Compressor
│   │   └── protocol.py     # Protocols & Enums
│   ├── capabilities/       # 能力实现
│   │   ├── mcp.toml        # Global MCP Configuration
│   │   ├── agents/         # Agents Root
│   │   │   ├── [agent_name]/   # Agent Package
│   │   │   │   ├── agent.py    # Implementation (inherits BaseAgent)
│   │   │   │   ├── tools/      # Agent-specific tools
│   │   │   │   └── mcp.toml    # Agent-specific MCP config
│   │   ├── tools/          # Global Shared Tools
│   └── utils/
└── logs/
```

## 技术栈
*   **语言**: Python 3.10+
*   **LLM 接口**: `openai` (AsyncOpenAI)
*   **配置解析**: `tomllib` (Python 3.11+) 或 `toml`
*   **异步框架**: `asyncio`

## 下一步计划
1.  搭建包含 `config/` 和 `src/` 的项目结构 (Completed)。
2.  实现 `Config` 类，支持 TOML 读取和模型切换逻辑 (Completed)。
3.  实现 `UnifiedRegistry` 和三种 Capability 的基础类 (Completed)。
4.  实现 `Orchestrator` 的 ReAct 核心循环 (Completed)。
5.  实现持久化任务列表 (Persistent Task List) (Completed)。
6.  实现 Context Compressor (Completed)。
7.  实现 Agent 标准化汇报协议 (Completed)。

### 7. CLI Agent 集成 (Qwen-Code / Claude-Code)
### 7. CLI Agent 集成 (Standard Sub-Agent Runtime)
**目标**: 将外部命令行 Agent (Qwen-Code/Claude-Code) 接入 OneAgent 体系，使其行为符合 OneAgent 协议。
**方案**: **OneAgent Runtime (MCP Server)**。
*   **概念转变**: MCP Server 不再暴露全局工具，而是提供一套 **"标准子 Agent 基础设施" (Standard Sub-Agent Toolset)**。
*   **核心工具**: 
    *   `report_status`: 用于汇报任务结果 (`SUCCESS`/`FAILURE`)，或请求中断 (`INTERRUPTED`) 以申请上级能力。
    *   *注: CLI Agent 通过此工具与 Orchestrator 进行协议级通信。*
*   **身份识别 (Identity Injection)**:
    *   通过 `--agent-name` 参数在启动时注入身份，解决 MCP Stdio 无状态问题。
*   **工作流**:
    1.  Orchestrator 决定调用 CLI Agent (如 Claude)。
    2.  Orchestrator 启动 CLI 进程，并监听标准化输出。
    3.  CLI Agent 启动自带的 MCP Client，连接 OneAgent Runtime。
    4.  CLI Agent 思考并调用 `report_status` 完成交互。

### 8. 结构化日志系统 (Structured Logging)
**目标**: 完整记录 "Orchestrator -> Agent -> Tool" 的调用链路和中间状态，便于调试和审计。
**实现**: `src/core/logger.py`
*   **格式**: JSONL (每行一个 JSON 对象)。
*   **核心字段**:
    *   `trace_id`: 全局请求 ID。
    *   `span_id`: 当前执行单元 ID。
    *   `parent_span_id`: 上级调用者 ID。
    *   `event`: `TASK_START`, `THOUGHT`, `TOOL_CALL`, `TOOL_RESULT`, `TASK_END`。
    *   `agent`: 当前 Agent 名称。
    *   `content`: 详细内容 (Prompt, Result, Error)。
*   **存储**: `logs/{date}.log`。

### 9. 会话管理系统 (Session Management)
**目标**: 支持持久化会话，随时恢复上下文 (Context Restoration)。
**实现**: `src/core/session.py`
*   **Session State**:
    *   `session_id`: UUID。
    *   `history`: 完整的对话历史 (Messages)。
    *   `task_list`: 当前任务列表状态。
    *   `variables`: 运行时变量 (Scratchpad)。
*   **Persistence**: 本地 JSON 文件 (`logs/sessions/{session_id}.json`)。
*   **Orchestrator 集成**:
    *   `__init__(session_id=None)`: 如果提供 ID，则加载历史状态。
    *   每次交互结束自动保存。

### 10. Web Interface & MCP HTTP Server
**目标**: 提供可视化的交互界面，并作为 MCP HTTP Server 运行。
**实现**: `src/server/web_server.py` (FastAPI)
*   **后端 API**:
    *   `POST /api/chat`: 发送消息 (Stream Response)。
    *   `POST /api/sessions`: 创建新会话。
    *   `GET /api/sessions`: 列出所有历史会话。
    *   `POST /api/sessions/{id}/resume`: 恢复会话。
    *   `POST /api/sessions/{id}/rewind`: 回滚到指定 turn。
*   **MCP Integration**:
    *   `GET /sse`: MCP SSE Endpoint for tool exposure.
    *   `POST /messages`: MCP Protocol messages.
*   **前端 (Modern UI)**:
    *   Technology: Vanilla HTML/JS/CSS (No build step).
    *   Style: Dark Mode, Glassmorphism, Responsive.
    *   Features:
        *   Sidebar with Session History.
        *   Chat Area with Streaming.
        *   Controls: "New Chat", "Rewind" (on message hover), "Resume" (click sidebar).

### 6. 未来扩展：分布式集群 (Distributed Network)
**核心思想**: 保持交互协议不变，将 `BaseAgent` 的 Python 调用映射为网络 API 调用。

1.  **分形架构 (Fractal Architecture)**:
    *   **主控节点 (Cluster Orchestrator)**: 一个运行在管理机上的 OneAgent。
    *   **工作节点 (Worker Node)**: 运行在不同机器上的 OneAgent 实例。
    *   **透明代理 (Remote Agent Adapter)**: 在主控节点上通过一个特殊的 `RemoteAgent` (继承 `BaseAgent`) 来封装对 Worker Node 的 HTTP 请求。

2.  **协议映射 (Protocol Mapping)**:
    *   **Capabilities Discovery**: `GET /api/v1/capabilities` -> 返回该节点的各种工具和 Agent 描述。
    *   **Dispatch**: `POST /api/v1/execute` (Body: `{ "instruction": "...", "context": "..." }`) -> 对应 `agent.execute()`.
    *   **Reporting**: HTTP Response Body (JSON: `{ "status": "INTERRUPTED", "result": "Requesting tool..." }`) -> 对应 `ExecutionResult`.

通过这种设计，主控 Agent 根本不需要知道下级是本地的 Python 类还是远程的服务器，它只需要处理标准的 `REJECTED/INTERRUPTED` 信号即可。整个网络的协作逻辑与单机完全一致。
