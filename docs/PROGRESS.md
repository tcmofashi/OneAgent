# OneAgent 项目进度追踪

> 最后更新: 2026-01-03

## 已完成功能 ✅

### 核心框架
- [x] **多 LLM Provider 支持** - DeepSeek, SiliconFlow, Google, Baidu, Zhipu, Ali
- [x] **功能角色模型配置** - 不同任务使用不同模型 (orchestrator, compressor, code_generation)
- [x] **全局配置系统** - `config.toml` 统一管理

### Orchestrator 主控
- [x] **ReAct 循环** - 流式输出思考过程
- [x] **工具调用** - 自动解析和执行工具
- [x] **任务列表管理** - 持久化任务状态
- [x] **子 Agent 调用** - 自动拦截并压缩上下文
- [x] **运行时工具隔离** - runtime tools 自动对 Orchestrator 不可见 (新增)
- [x] **用户输入工具** - `request_user_input` 请求用户输入或等待用户操作 (新增)

### 标准子 Agent 工作流
- [x] **标准输入定义** - instruction, context, upstream_capabilities
- [x] **标准系统提示模板** - 中英文双语，包含任务、身份、规范等
- [x] **标准工具** - report_status (SUCCESS/FAILURE/REJECTED/INTERRUPTED)
- [x] **ReactAgent 基类** - 原生 ReAct 循环能力，支持从 config.toml 选择模型 (新增)
- [x] **HelloWorldAgent 改造** - 继承 ReactAgent，代码从 123 行精简到 34 行

### Qwen Code CLI 集成 (新增)
- [x] **QwenBridgeAgent** - 通过 CLI 桥接脚本调用 Qwen Code
- [x] **流式输出美化** - 使用 stream-json 格式实时显示思考、工具调用、结果
- [x] **完整 Prompt 显示** - 启动时显示传递给子代理的完整 Prompt
- [x] **Debug 信息过滤** - 隐藏 MemoryDiscovery、BfsFileSearch 等调试输出
- [x] **report_status 工具** - Qwen CLI 内置工具，用于向上级报告任务状态

### 能力注册系统
- [x] **全局工具注册** - SystemInfoTool, RequestUserInputTool
- [x] **作用域工具** - 每个 Agent 可有专属工具
- [x] **能力树状图** - 供上下文压缩和子 Agent 使用
- [x] **运行时工具标记** - `is_runtime_tool` 参数区分子代理专用工具 (新增)
- [x] **工具黑名单/白名单** - `get_all_tool_schemas` 支持 blacklist/whitelist (新增)

### 上下文压缩
- [x] **ContextCompressor** - 压缩历史对话为关键信息
- [x] **任务相关性过滤** - 只传递与子 Agent 任务相关的上下文

### Web UI
- [x] **Vue.js 前端** - 现代化聊天界面
- [x] **WebSocket 实时通信** - 流式消息显示
- [x] **会话管理** - 多会话支持

### MCP 集成
- [x] **Claude MCP Client** - 让 Claude Code 作为子 Agent
- [x] **从 config.toml 读取配置** - 与主服务器共用配置
- [x] **标准 report_status 工具** - 统一的状态报告接口

### CLI 模式
- [x] **命令行交互** - `main.py` 入口
- [x] **流式事件显示** - 思考、工具调用、结果

---

## 本次更新内容 (2026-01-03) 🆕

### ReactAgent 基类
新增 `src/core/react_agent.py`，提供原生 ReAct 循环能力：
- `model_role`: 从 config.toml 的 functional_roles 选择模型
- `model_label`: 直接指定模型标签
- `max_iterations`: 可配置的最大迭代次数
- 自动处理工具调用和 report_status 终止信号

### 运行时工具隔离
- Registry 新增 `_runtime_tools` 集合跟踪子代理专用工具
- `register()` 新增 `is_runtime_tool` 参数
- `get_all_tool_schemas()` 新增 `exclude_runtime_tools` 参数
- Orchestrator 自动排除所有运行时工具

### 用户输入工具
新增 `src/capabilities/tools/request_user_input.py`：
- 请求用户输入文本
- 等待用户完成操作后按 Enter 继续

### Qwen CLI 输出美化
- 使用 `stream-json` 格式实现真正的流式输出
- 使用 emoji 美化显示（💭思考、🔧工具、📋结果、✅状态）
- 启动时显示完整 Prompt 内容
- 过滤 debug 信息

### 子 Agent Prompt 修复
- 模板添加 `## 你的任务/{instruction}` 部分
- `build_full_prompt()` 新增 `instruction` 参数
- 确保任务指令正确传递给子代理

---

## 未来计划 📋

### 短期目标
- [ ] **更多内置 Agent** - 代码生成 Agent, 文件操作 Agent
- [ ] **Agent 状态回调** - 子 Agent 可以请求上级帮助 (INTERRUPTED 状态)
- [ ] **MCP 工具转发** - 将 MCP Server 的工具暴露给子 Agent

### 中期目标
- [ ] **多 Agent 协作** - Agent 之间的消息传递
- [ ] **工作流定义** - YAML/TOML 定义复杂工作流
- [ ] **插件系统** - 第三方能力包

### 长期目标
- [ ] **分布式执行** - 多机 Agent 集群
- [ ] **安全沙箱** - 代码执行隔离
- [ ] **可视化工作流编辑器** - Web UI 拖拽编排

---

## 文件结构

```
OneAgent/
├── config/
│   ├── config.toml          # 主配置文件
│   └── config.template.toml
├── src/
│   ├── core/
│   │   ├── orchestrator.py   # 主控编排器
│   │   ├── capability.py     # 能力基类 (BaseAgent, BaseTool)
│   │   ├── react_agent.py    # ReactAgent 基类 (新增)
│   │   ├── compressor.py     # 上下文压缩
│   │   ├── registry.py       # 能力注册表
│   │   └── ...
│   ├── capabilities/
│   │   ├── agents/           # 子 Agent
│   │   │   ├── hello_world_agent/
│   │   │   └── qwen_agent/   # Qwen CLI 集成
│   │   └── tools/            # 全局工具
│   │       ├── system_info.py
│   │       └── request_user_input.py (新增)
│   ├── runtime_tools/        # 运行时工具 (子代理专用)
│   │   └── report_status.py
│   ├── server/
│   │   ├── web_server.py     # FastAPI 服务器
│   │   ├── mcp_server.py     # MCP 标准服务器
│   │   └── ui/               # Vue.js 前端
│   └── utils/
│       └── loader.py         # 能力加载器
└── main.py                   # CLI 入口
```

---

## 相关文档

- [实施计划](../IMPLEMENTATION_PLAN.md) - 详细的技术设计
- [CLAUDE.md](../CLAUDE.md) - Claude Code 集成指南
- [QWEN.md](../QWEN.md) - Qwen Code 集成指南 (新增)
