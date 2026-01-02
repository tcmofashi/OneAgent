# OneAgent - Claude Code 集成指南

## MCP 集成说明

OneAgent 提供了一个 MCP (Model Context Protocol) 服务器，允许 Claude Code 作为 OneAgent 的子代理参与任务执行。

### 重要提示

**此 MCP 仅在被 OneAgent 调用执行任务时需要使用。平时对话中不需要调用此 MCP 的工具。**

### 可用工具

| 工具名称            | 用途                           | 何时使用               |
| ------------------- | ------------------------------ | ---------------------- |
| `report_status`     | 向 OneAgent 主控报告任务状态   | 当作为子代理执行任务时 |
| `get_task_context`  | 获取 OneAgent 分配的任务上下文 | 需要了解任务详情时     |
| `list_capabilities` | 列出 OneAgent 系统中的可用能力 | 需要了解系统能力时     |

### 使用场景

1. **被 OneAgent 调用时**：
   - OneAgent 主控会分配任务给 Claude
   - 使用 `report_status` 报告进度和结果
   - 状态类型：`in_progress`, `completed`, `failed`, `need_help`, `blocked`

2. **正常对话时**：
   - 不需要使用这些工具
   - 按正常方式响应用户

### 配置要求

确保 OneAgent Web Server 正在运行：
```bash
cd /home/tcmofashi/proj/OneAgent
uv run uvicorn src.server.web_server:app --host 0.0.0.0 --port 8000
```

### 项目结构

```
OneAgent/
├── src/
│   ├── core/           # 核心框架
│   │   ├── orchestrator.py  # 主控编排器
│   │   └── ...
│   ├── server/         # 服务器
│   │   ├── web_server.py    # FastAPI Web 服务器
│   │   └── oneagent_mcp_client.py  # Claude MCP 客户端
│   └── capabilities/   # 能力（工具和代理）
└── config/             # 配置文件
```
