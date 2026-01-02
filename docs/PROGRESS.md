# OneAgent 项目进度追踪

> 最后更新: 2026-01-02

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

### 标准子 Agent 工作流 (新完成)
- [x] **标准输入定义** - instruction, context, upstream_capabilities
- [x] **标准系统提示模板** - 中英文双语
- [x] **标准工具** - report_status (SUCCESS/FAILURE/REJECTED/INTERRUPTED)
- [x] **HelloWorldAgent 改造** - 遵循标准工作流范式

### 能力注册系统
- [x] **全局工具注册** - SystemInfoTool, ReportStatusTool
- [x] **作用域工具** - 每个 Agent 可有专属工具
- [x] **能力树状图** - 供上下文压缩和子 Agent 使用

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

## 进行中 🚧

- [x] **JSON 解析优化** - 使用 `json_cleaner` 模型修复损坏的 JSON（已完成）


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
│   │   ├── capability.py     # 能力基类
│   │   ├── compressor.py     # 上下文压缩
│   │   ├── registry.py       # 能力注册表
│   │   └── ...
│   ├── capabilities/
│   │   ├── agents/           # 子 Agent
│   │   │   └── hello_world_agent/
│   │   └── tools/            # 全局工具
│   ├── runtime_tools/        # 运行时工具 (report_status)
│   ├── server/
│   │   ├── web_server.py     # FastAPI 服务器
│   │   ├── mcp_server.py     # MCP 标准服务器
│   │   ├── oneagent_mcp_client.py  # Claude MCP 客户端
│   │   └── ui/               # Vue.js 前端
│   └── utils/
│       └── loader.py         # 能力加载器
└── main.py                   # CLI 入口
```

---

## 相关文档

- [实施计划](../docs/implementation_plan.md) - 详细的技术设计
- [CLAUDE.md](../CLAUDE.md) - Claude Code 集成指南
