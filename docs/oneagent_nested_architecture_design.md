# Nested OneAgent Orchestration System - Architecture Design

## 一、设计目标

### 1.1 核心需求
实现 OneAgent 的嵌套编排系统，使所有 OneAgent 都可以作为**父 Agent**和**子 Agent**对称存在：

1. **标准化输入输出**
   - 包含规划期和子 Agent 的输入/输出
   - 支持流式结果反馈

2. **灵活的网络协议**
   - **选项 A**: WebSocket + 心跳机制（实时推送，推荐用于交互场景）
   - **选项 B**: HTTP + 调用时长限制（同步调用，推荐用于管理/控制场景）

3. **对称嵌套能力**
   - 所有 OneAgent 可作为父 Agent 嵌套子 OneAgent
   - 子 OneAgent 可调用其他子 OneAgent（多层嵌套）
   - 对称：支持 OneAgent 对 OneAgent，OneAgent 对普通工具

4. **外部 API 能力**
   - 最上层 OneAgent 对外提供标准化 API
   - 支持任务编排、能力树查询、会话管理
   - 使用自定义协议（非 OpenAI）

5. **纯 Python 实现**
   - 使用 Python 实现所有组件
   - 所有 OneAgent 对称，支持 runtime 工具

## 二、整体架构设计

### 2.1 架构图

```
┌─────────────────────────────────────────────────────────────────────┐
│                    External API Gateway                              │
│              (Custom JSON Protocol, FastAPI)                         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
            RootOneAgent (Orchestrator 扩展)
            ┌──────────────────┴──────────────────────┐
            │                                  │
   SubOneAgent Layer 1 (父 Agent，可嵌套子 Agent)
   ┌──────────────┬───────────────────┐
   │            │                   │
   SubOneAgent Layer 2 (子 OneAgent)
   ┌──────────┬──────┐
   │            │     └─────────┐
SubOneAgent Layer N (最底层)
   │            │           Tools (bash, file, etc.)
   └──────────────┘
```

### 2.2 核心设计原则

1. **对称性原则**
   - 任何 OneAgent 既可以是父 Agent 也可以是子 Agent
   - OneAgent 调用 OneAgent 和调用工具行为一致
   - 不区分"主-子"关系，统一为"调用者-被调用者"

2. **协议无关性**
   - 内部 OneAgent 间通信使用统一的 BaseAgent 接口
   - 外部 API 使用自定义 JSON 协议
   - 网络协议与内部逻辑解耦

3. **Runtime 工具单独列出**
   - 子 Agent 的 runtime 工具不嵌入能力树
   - 在能力树响应中单独列出
   - 对于拥有自有工具的 Agent（如 Qwen Code），需要在描述中详细说明

## 三、协议设计

### 3.1 自定义 JSON 协议（非 OpenAI）

**设计理由**：需要灵活的元数据支持、会话管理、多层嵌套，OpenAI 格式不够灵活

#### 3.1.1 协议版本和类型

```json
{
  "protocol": "OneAgentNested",
  "version": "1.0",
  "encoding": "UTF-8"
}
```

#### 3.1.2 消息类型定义

##### A. 握手消息
```json
{
  "type": "handshake",
  "protocol": "ws|http",
  "agent_id": "uuid",
  "session_id": "uuid"
}
```

##### B. 心跳消息
```json
{
  "type": "heartbeat",
  "session_id": "uuid",
  "timestamp": "ISO8601"
}
```

##### C. 调用消息
```json
{
  "type": "call_agent",
  "caller_agent_id": "uuid",
  "target_agent_id": "uuid",
  "instruction": "string",
  "context": "string",
  "parameters": {},
  "timeout": 120,
  "expect_stream": true
}
```

##### D. 输出消息
```json
{
  "type": "output",
  "session_id": "uuid",
  "timestamp": "ISO8601",
  "content": "string",
  "done": false
}
```

##### E. 能力树查询
```json
{
  "type": "get_capabilities",
  "agent_id": "uuid"
}
```

##### F. 能力树响应
```json
{
  "type": "capabilities",
  "session_id": "uuid",
  "data": {
    "agent": {
      "id": "uuid",
      "name": "string",
      "custom_type": "root_agent|sub_agent",
      "description": "string"
    },
    "children": [
      // 子 Agent 和工具列表（不包括 runtime 工具）
    ],
    "runtime_tools": [
      // 子 Agent 的 runtime 工具列表（单独列出）
    ]
  }
}
```

##### G. 完成消息
```json
{
  "type": "complete",
  "session_id": "uuid",
  "result": "success|error"
}
```

## 四、核心组件设计

### 4.1 RootOneAgent 扩展

基于现有的 `Orchestrator`，扩展为支持嵌套编排的 `RootOneAgent`：

```python
class RootOneAgent(BaseAgent):
    """
    顶层 OneAgent，具备嵌套编排和外部 API 能力
    """

    # ========== 新增接口 ==========

    # 1. 嵌套调用接口
    async def call_nested_agent(
        self,
        agent_id: str,
        instruction: str,
        context: str = "",
        parameters: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        调用嵌套的 OneAgent
        返回格式：{status, result, output_stream}
        """
        pass

    # 2. 能力树查询接口
    async def get_capabilities_tree(
        self,
        agent_id: str
    ) -> Dict[str, Any]:
        """
        查询指定 OneAgent 的能力树
        返回格式：{agent, children, runtime_tools}
        """
        pass

    # 3. 嵌套会话管理接口
    async def create_nested_session(
        self,
        parent_agent_id: str,
        session_config: Dict[str, Any] = None
    ) -> str:
        """
        创建嵌套会话，返回 session_id
        """
        pass

    async def close_nested_session(
        self,
        session_id: str
    ) -> bool:
        """
        关闭嵌套会话
        """
        pass
```

### 4.2 SubOneAgent 扩展

所有 OneAgent 默认继承 `BaseAgent`，新增嵌套调用能力和 runtime 工具支持：

```python
class SubOneAgent(BaseAgent):
    """
    嵌套 OneAgent，支持被父 OneAgent 调用
    """

    # ========== 新增属性 ==========
    parent_agent_id: Optional[str] = None  # 父 Agent ID
    parent_session_id: Optional[str] = None  # 父会话 ID
    runtime_tools: List[ToolSchema] = []  # Runtime 工具列表

    # ========== 新增接口 ==========

    # 1. 嵌套调用接口
    async def call_nested_agent(
        self,
        agent_id: str,
        instruction: str,
        context: str = ""
    ) -> Dict[str, Any]:
        """调用更底层的 OneAgent"""
        pass

    # 2. 能力树查询接口
    async def get_capabilities(
        self,
        include_children: bool = True
    ) -> Dict[str, Any]:
        """
        返回自身 + 子 Agent 的能力树（runtime 工具单独列出）
        返回格式：{agent, children, runtime_tools}
        """
        pass
```

### 4.3 能力树数据结构

```python
@dataclass
class CapabilityTreeNode:
    """能力树节点（不包括 runtime 工具）"""
    id: str
    name: str
    description: str
    type: CapabilityType  # root_agent, sub_agent, tool
    parent_id: Optional[str]
    children: List[CapabilityTreeNode]
    parameters: Dict[str, Any]

@dataclass
class RuntimeTool:
    """Runtime 工具（单独列出）"""
    id: str
    name: str
    description: str
    parameters: Dict[str, Any]

@dataclass
class NestedAgentCapabilities:
    """嵌套 OneAgent 能力集合"""
    agent: CapabilityTreeNode  # 根节点（自身）
    children: List[CapabilityTreeNode]  # 子 OneAgent 和工具（不包括 runtime）
    runtime_tools: List[RuntimeTool]  # Runtime 工具列表（单独列出）
```

## 五、会话管理设计

### 5.1 会话层级

```python
@dataclass
class Session:
    """会话对象"""
    session_id: str
    parent_session_id: Optional[str]
    agent_id: str
    created_at: str
    last_activity: str
    status: SessionStatus
    metadata: Dict[str, Any]

class SessionStatus(Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    ERROR = "error"
```

### 5.2 嵌套会话管理器

```python
class RootOneAgentSessionManager:
    """管理所有嵌套会话"""

    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.nested_sessions: Dict[str, List[Session]] = {}
```

**关键特性**：
- 支持创建会话时指定父会话 ID
- 自动维护父子会话关联
- 关闭会话时自动关闭相关子会话
- 超时自动清理

## 六、标准化输入输出设计

### 6.1 规划期输出

```json
{
  "planning_period": {
    "start_time": "2025-01-20T10:00:00Z",
    "end_time": "2025-01-20T10:30:00Z",
    "agents": [
      {
        "agent_id": "root_agent_001",
        "type": "root_agent",
        "planned_tasks": [
          {
            "id": "task_001",
            "description": "创建用户账户",
            "estimated_duration": 300,
            "assigned_to": "web_agent_001"
          }
        ]
      }
    ]
  }
}
```

### 6.2 子 Agent 输入/输出日志

```json
{
  "execution_log": {
    "agent_id": "web_agent_001",
    "output": {
      "type": "nested_call_received",
      "timestamp": "2025-01-20T10:15:00Z",
      "data": {
        "input": {
          "from_agent": "root_agent_001",
          "input": {
            "instruction": "create user account",
            "parameters": {}
          }
        }
      }
    }
  },
  "output_stream": [
    {
      "timestamp": "2025-01-20T10:16:00Z",
      "type": "thinking",
      "content": "分析用户需求..."
    },
    {
      "timestamp": "2025-01-20T10:17:00Z",
      "type": "tool_call",
      "content": "调用 createUser API"
    },
    {
      "timestamp": "2025-01-20T10:25:00Z",
      "type": "task_result",
      "content": "用户账户创建成功，ID: user_12345"
    }
  ]
}
```

## 七、文件结构

```
OneAgent/
├── src/
│   ├── core/
│   │   ├── orchestrator.py              # 现有
│   │   ├── base_agent.py               # 现有
│   │   ├── root_one_agent.py           # 新建：RootOneAgent 实现
│   │   └── sub_one_agent.py            # 新建：SubOneAgent 实现
│   │
│   ├── server/
│   │   ├── ws_gateway.py               # 新建：WebSocket 网关
│   │   ├── http_gateway.py              # 新建：HTTP 网关
│   │   └── api.py                    # 新建：统一 API 入口
│   │
│   ├── models/
│   │   ├── requests.py                 # 新建：请求数据模型
│   │   ├── responses.py                # 新建：响应数据模型
│   │   ├── protocol.py                 # 新建：协议定义
│   │   ├── capability_tree.py           # 新建：能力树实现
│   │   └── session.py                 # 新建：会话模型
│   │
│   └── utils/
│       └── config.py                  # 新建：配置加载
│
├── docs/
│   └── oneagent_nested_architecture_design.md  # 本文档
│
├── config/
│   └── oneagent_config.toml          # 新建：OneAgent 配置
│
└── examples/
    └── nested_call_example.py            # 待创建：使用示例
```

## 八、关键技术决策

### 8.1 Runtime 工具设计

**决策理由**：
1. **工具类型差异**：SubOneAgent 的 runtime 工具与普通工具不同，需要单独管理
2. **描述灵活性**：对于 Qwen Code 等拥有大量自有工具的 Agent，需要在描述中详细说明，无法自动获取
3. **能力树清晰性**：将 runtime 工具单独列出，使能力树更加清晰

**实现方式**：
- `CapabilityTreeNode` 只包含子 Agent 和普通工具
- `RuntimeTool` 单独列表存储在 `NestedAgentCapabilities` 中
- Agent 的 `description` 字段用于详细说明自有工具能力

### 8.2 为什么不使用 OpenAI 协议

**决策理由**：
1. **元数据支持需求**：需要支持复杂的会话层级（父-子关系）
2. **多层嵌套需求**：需要支持 Agent 调用 Agent 调用 Agent 的无限嵌套
3. **灵活性需求**：需要自定义协议版本、编码等字段
4. **Runtime 工具需求**：需要单独列出 runtime 工具

### 8.3 为什么使用纯 Python

**决策理由**：
1. **与现有代码一致**：OneAgent 当前是 Python 实现
2. **快速开发**：开发速度快，易于调试和维护
3. **对称性实现**：更容易实现所有 OneAgent 对称的设计

## 九、总结

### 9.1 设计要点回顾

| 要点 | 设计方案 |
|------|---------|
| **对称性** | 所有 OneAgent 可作为父/子 Agent，统一接口 |
| **协议设计** | 自定义 JSON 协议，支持 WebSocket 和 HTTP |
| **会话管理** | 多层嵌套会话，自动清理，超时控制 |
| **能力树** | 子 Agent 和工具，runtime 工具单独列出 |
| **Runtime 工具** | 在 `runtime_tools` 列表中单独管理，不嵌入能力树 |
| **标准化输入输出** | 规划期输出、嵌套调用日志、流式结果 |
| **外部 API** | 统一网关，支持任务编排、能力查询、会话管理 |
| **实现语言** | 纯 Python |

### 9.2 优先级建议

**高优先级（立即实施）**：
1. ✅ 实现协议数据模型
2. ✅ 实现能力树数据结构（runtime 单独列出）
3. ✅ 实现会话数据模型和管理器
4. ✅ 扩展 `BaseAgent` 为 `RootOneAgent` 和 `SubOneAgent`
5. ✅ 实现 WebSocket 网关

**中优先级（第二阶段）**：
6. ✅ 实现 HTTP 网关
7. ✅ 完善能力树递归查询
8. ✅ 集成到 FastAPI 应用
9. ✅ 创建配置文件

**低优先级（第三阶段）**：
10. ✅ 编写使用示例
11. ✅ 添加单元测试和集成测试
12. ✅ 性能优化

---

**设计文档完成** 🎉

这是一个完整的嵌套 OneAgent 编排系统架构设计，重点关注：
- ✅ 纯 Python 实现
- ✅ 所有 OneAgent 对称，支持嵌套
- ✅ Runtime 工具单独列出，不嵌入能力树
- ✅ 对拥有自有工具的 Agent，在描述中详细说明
- ✅ SubOneAgent 也支持 runtime 工具
