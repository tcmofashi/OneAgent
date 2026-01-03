# OneAgent - Qwen Code 集成指南

## Qwen Bridge Agent 概述

Qwen Bridge Agent 是一个将 Qwen Code CLI 集成到 OneAgent 框架中的适配器代理。它允许 Qwen Code 作为 OneAgent 的标准子代理，遵循 OneAgent 的协议和工作流规范。

### 核心特性

- **标准子代理工作流**：遵循 OneAgent 的标准输入输出格式
- **流式输出处理**：实时解析和格式化 Qwen Code 的输出
- **状态报告集成**：通过 `report_status` 工具与 OneAgent 主控通信
- **多模型支持**：继承 OneAgent 的模型配置系统
- **上下文压缩**：自动接收压缩后的上下文和上级能力列表

### 架构设计

```
Qwen Bridge Agent 工作流：
OneAgent Orchestrator → QwenBridgeAgent → oneagent-bridge.js → Qwen Code CLI
```

## 使用说明

### 作为子代理被调用时

当 OneAgent 主控调用 Qwen Bridge Agent 时，会提供以下标准输入：

1. **instruction**：具体任务指令
2. **context**：压缩后的相关上下文
3. **upstream_capabilities**：可用的上级工具列表（需通过 INTERRUPTED 状态申请使用）

### 标准工具

Qwen Bridge Agent 可使用以下标准工具：

| 工具名称 | 用途 | 参数 |
|---------|------|------|
| `report_status` | 向 OneAgent 主控报告任务状态 | `status` (success/failure/rejected/interrupted), `summary` |

### 状态报告协议

Qwen Bridge Agent 必须通过 `report_status` 工具报告执行结果：

1. **SUCCESS**：任务成功完成
2. **FAILURE**：执行失败（客观原因）
3. **REJECTED**：拒绝执行（任务不合理/超出范围）
4. **INTERRUPTED**：请求中断（需上级协助）

### 输出格式

Qwen Bridge Agent 会实时格式化 Qwen Code 的输出，包括：

- 💭 思考过程
- 🔧 工具调用
- 📋 工具结果
- ✅ 状态报告
- 🏁 完成状态

## 配置与部署

### 前置要求

1. **Node.js**：运行桥接脚本所需
2. **Qwen Code CLI**：已安装并配置
3. **API 密钥**：在 config.toml 中配置 LLM 提供商

### 配置文件

确保 `config/config.toml` 正确配置：

```toml
[llm]
active_provider = "siliconflow"
active_model_label = "deepseek-v3"  # 或使用 qwen 专用模型

[llm.providers.siliconflow]
api_base = "https://api.siliconflow.cn/v1"
api_key = "YOUR_API_KEY_HERE"

[llm.models]
qwen-coder = { provider = "siliconflow", model_name = "Qwen/Qwen2.5-Coder-32B-Instruct" }
```

### 桥接脚本

Qwen Bridge Agent 使用预编译的桥接脚本：

```
src/capabilities/agents/qwen_agent/cli_dist/dist/oneagent-bridge.js
```

该脚本处理与 Qwen Code CLI 的通信，并将输出转换为 OneAgent 标准格式。

## 开发与调试

### 查看完整输出

要查看 Qwen Code 的完整输出（包括调试信息），可以修改 `agent.py` 中的 `DEBUG_PATTERNS` 列表。

### 自定义模型

在 `agent.py` 中修改 `target_model_label` 逻辑：

```python
target_model_label = global_config.get("llm.functional_roles.code_generation")
if not target_model_label:
    target_model_label = global_config.get("llm.active_model_label")
```

### 环境变量

桥接脚本使用以下环境变量：

- `OPENAI_API_KEY`：API 密钥
- `OPENAI_BASE_URL`：API 基础 URL

## 示例任务

### 代码生成任务

```
指令：为 OneAgent 创建一个简单的文件读取工具
上下文：OneAgent 使用 Python 3.10+，已有 BaseTool 基类
上级能力：文件系统访问权限（需通过 INTERRUPTED 申请）
```

### 错误处理

当遇到权限问题时，Qwen Bridge Agent 应：

1. 识别问题
2. 使用 `report_status` 报告 `INTERRUPTED` 状态
3. 在 summary 中说明需要什么工具/权限
4. 等待 OneAgent 主控处理并重新调度

## 故障排除

### 常见问题

1. **桥接脚本未找到**：检查 `BRIDGE_SCRIPT_PATH` 是否正确
2. **API 配置错误**：验证 config.toml 中的 API 配置
3. **输出解析失败**：检查 Qwen Code 的输出格式是否符合预期
4. **权限问题**：确保有足够的文件系统权限

### 日志查看

Qwen Bridge Agent 会过滤调试信息，要查看完整日志：

1. 修改 `_should_filter_line` 方法
2. 或直接查看 Qwen Code CLI 的原始输出

## 与其他代理的对比

| 特性 | Qwen Bridge Agent | Claude Agent |
|------|-------------------|--------------|
| 集成方式 | CLI 桥接脚本 | MCP 协议 |
| 通信协议 | 标准子代理协议 | MCP + 标准协议 |
| 工具支持 | report_status 等标准工具 | 完整 MCP 工具集 |
| 输出处理 | 实时流式格式化 | MCP 消息传递 |

## 未来扩展

### 计划功能

1. **直接工具调用**：允许 Qwen Code 直接调用上级工具（无需 INTERRUPTED）
2. **多会话支持**：保持 Qwen Code 会话状态
3. **性能优化**：减少启动开销
4. **自定义提示模板**：针对不同任务优化提示

### 贡献指南

要改进 Qwen Bridge Agent：

1. 修改 `src/capabilities/agents/qwen_agent/agent.py`
2. 更新桥接脚本 `cli_dist/dist/oneagent-bridge.js`
3. 添加相应的测试用例
4. 更新本文档

## 相关资源

- [OneAgent 实施计划](../docs/IMPLEMENTATION_PLAN.md)
- [Claude Code 集成指南](../CLAUDE.md)
- [Qwen Code 官方文档](https://github.com/QwenLM/Qwen2.5-Coder)

---

**最后更新**：2026年1月3日  
**版本**：1.0.0  
**维护者**：OneAgent 开发团队