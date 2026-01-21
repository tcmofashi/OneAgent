# 嵌套 OneAgent 测试指南

本目录包含完整的测试套件，用于验证嵌套 OneAgent 编排系统的功能。

## 测试结构

```
tests/
├── test_root_one_agent.py        # RootOneAgent 单元测试
├── test_sub_one_agent.py         # SubOneAgent 单元测试
├── test_session_manager.py        # 会话管理器单元测试
└── test_integration.py            # 集成测试（端到端）
```

## 测试类型

### 1. 单元测试

测试各个模块的独立功能。

```bash
# 运行所有单元测试
pytest tests/ -v

# 运行特定测试文件
pytest tests/test_root_one_agent.py -v
pytest tests/test_sub_one_agent.py -v
pytest tests/test_session_manager.py -v
```

### 2. 集成测试

测试端到端的功能。

```bash
# 运行所有集成测试
pytest tests/test_integration.py -v
```

### 3. 手动验证

运行示例代码验证功能：

```bash
python examples/nested_call_example.py
```

---

## 测试覆盖率

### 单元测试覆盖

| 模块 | 测试覆盖 |
|------|---------|
| RootOneAgent | 初始化、启动/停止、注册子 Agent、嵌套调用、能力树查询、会话管理 |
| SubOneAgent | 初始化、注册子 Agent、嵌套调用、能力查询、流式执行 |
| SessionManager | 初始化、创建会话、创建嵌套会话、会话过期、获取会话、关闭会话、嵌套会话查询、会话数量 |

### 集成测试覆盖

| 端点 | 测试场景 |
|------|---------|
| GET / | 健康检查 |
| GET /health | 健康检查 |
| GET /api/agent/capabilities | 能力树查询 |
| POST /api/agent/nested_call | 嵌套调用（非流式） |
| POST /api/agent/nested_call | 嵌套调用（流式） |
| POST /api/session/create | 会话创建 |
| GET /api/session/{session_id} | 会话查询 |
| POST /api/session/close | 会话关闭 |
| POST /api/heartbeat | 心跳机制 |

### 错误处理覆盖

| 错误类型 | 测试场景 |
|---------|---------|
| Agent 不存在 | 调用不存在的子 Agent |
| 会话不存在 | 查询/关闭不存在的会话 |
| 请求参数错误 | 缺少必需参数 |
| 网络错误 | 连接失败、超时 |

---

## 运行测试

### 1. 运行单元测试

```bash
# 运行所有单元测试
pytest tests/ -v --cov=src --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 2. 运行集成测试

```bash
# 运行集成测试（需要服务器启动）
# 先启动服务器
uvicorn src.server.api:app --host 0.0.0.0 --port 8000 &

# 然后运行测试
pytest tests/test_integration.py -v
```

### 3. 运行示例代码

```bash
# 运行示例代码
python examples/nested_call_example.py
```

预期输出：
```
=== 查询 RootOneAgent 能力树 ===
Agent: RootOneAgent
Children: 2
Runtime Tools: 0

=== 查询 WebAgent 能力树 ===
Agent: WebAgent
Description: 网页浏览代理。拥有以下 runtime 工具：playwright_navigate, playwright_click, playwright_screenshot。
Runtime Tools: 0

=== 查询 CodeAgent 能力树 ===
Agent: CodeAgent
Description (注意：此 Agent 的自有工具在 description 中详细说明）:
编程代理，拥有大量自有工具：code_analyze, code_execute, code_fix, code_test, code_refactor。

=== 演示嵌套调用 ===

[1] RootOneAgent -> WebAgent: 浏览网页
结果: 网页浏览成功

[2] RootOneAgent -> CodeAgent: 分析代码
结果: 代码分析完成

[3] RootOneAgent -> WebAgent: 流式输出
流式输出结果:
开始执行指令: 模拟长时间任务，流式输出结果
执行结果...

=== 演示会话管理 ===
创建会话: <session_id>
查询会话: <session_id>, 状态: active
关闭会话: True

=== 示例完成 ===
```

---

## 检查清单

运行测试后，验证以下功能：

- [ ] RootOneAgent 初始化成功
- [ ] RootOneAgent 启动和停止正常
- [ ] SubOneAgent 注册和嵌套调用
- [ ] 能力树查询返回正确数据
- [ ] Runtime 工具单独列出
- [ ] 会话创建、查询、关闭
- [ ] 嵌套会话管理
- [ ] HTTP API 端点响应正确
- [ ] WebSocket 握手和心跳
- [ ] 流式输出正常
- [ ] 错误处理正确
- [ ] 会话过期自动清理

---

## 故障排除

### 测试失败

如果测试失败，检查：

1. **依赖是否安装**：`pip install pytest pytest-asyncio httpx`
2. **端口是否被占用**：`lsof -i :8000`
3. **导入路径是否正确**：确认 `sys.path` 包含 `src/` 目录
4. **示例代码是否可运行**：手动运行示例代码

### LSP 错误

一些 LSP 错误已识别但不会影响功能：
- `orchestrator.py`: `ChatCompletionMessageCustomToolCall.function` - 这是上游代码的问题
- `react_agent.py`: 方法签名不匹配 - 这是现有代码的问题

这些错误可以忽略，不影响嵌套功能。

---

## 下一步

1. 运行所有测试
2. 检查测试覆盖率
3. 修复发现的问题
4. 添加更多测试场景
5. 性能测试和优化
