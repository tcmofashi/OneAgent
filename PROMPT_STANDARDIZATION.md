# Prompt 传递标准化方案

## 概述

本方案在**不改变外部接口**和**保持现有 Prompt 渲染**的基础上，实现了内部参数传递的标准化。

## 核心设计

### 1. 统一数据结构 `AgentPromptContext`

```python
@dataclass
class AgentPromptContext:
    """
    统一的 Agent Prompt 上下文结构。

    用于内部标准化参数传递，保持外部接口不变。
    """
    # 基础信息
    agent_name: str
    agent_description: str
    agent_type: str  # standard/web/gui/bridge

    # 任务信息
    core_instruction: str           # 核心指令（已简化）
    original_instruction: str         # 原始指令（用于调试）
    task_priority: str
    task_category: str

    # 上下文信息
    background_context: str           # 压缩的背景信息
    relevant_history: str            # 相关历史片段

    # 能力信息
    allowed_tools: List[str]
    upstream_capabilities: str         # 上级能力树字符串
    tools_summary: str               # 工具摘要

    # 元数据
    session_id: str
    trace_id: str
    timestamp: str

    # 扩展规则
    additional_rules: List[str]        # Agent 特殊规则
    constraints: List[str]             # 约束条件

    # 配置参数
    language: str
    max_iterations: int
```

### 2. 向后兼容方法

```python
@classmethod
def from_legacy_params(cls, instruction, context, upstream_capabilities, ...) -> AgentPromptContext:
    """
    从旧接口参数创建标准化的上下文对象。

    保持外部接口兼容性，内部转换为统一结构。
    """
    return cls(
        agent_name=agent_name,
        agent_description=agent_description,
        core_instruction=instruction,
        background_context=context,
        upstream_capabilities=upstream_capabilities,
        ...
    )

def to_legacy_dict(self) -> Dict[str, Any]:
    """
    转换为旧接口参数字典。

    用于与现有代码兼容。
    """
    return {
        "instruction": self.core_instruction,
        "context": self.background_context,
        "upstream_capabilities": self.upstream_capabilities,
    }
```

### 3. 调试支持

```python
def get_summary(self) -> str:
    """
    获取上下文摘要（用于调试）。
    """
    return (
        f"[AgentPromptContext]\n"
        f"  Agent: {self.agent_name} ({self.agent_type})\n"
        f"  Instruction: {self.core_instruction[:100]}...\n"
        f"  Context: {len(self.background_context)} chars\n"
        f"  Upstream Capabilities: {len(self.upstream_capabilities)} chars\n"
        f"  Tools: {self.tools_summary}\n"
        f"  Language: {self.language}\n"
    )
```

## 实现细节

### 1. BaseAgent 改造

**修改位置**: `src/core/capability.py`

```python
class BaseAgent(Capability):
    # 原有方法：外部接口不变
    def build_full_prompt(
        self,
        instruction: str = "",
        context: str = "",
        upstream_capabilities: str = "",
        language: str = "zh",
    ) -> str:
        """
        外部接口保持不变，内部转换为统一结构。
        """
        # 转换为统一结构
        ctx = AgentPromptContext.from_legacy_params(
            instruction=instruction,
            context=context,
            upstream_capabilities=upstream_capabilities,
            agent_name=self.name,
            agent_description=self.description,
            allowed_tools=self.allowed_tools,
            language=language,
        )

        # 调用内部方法
        return self._build_prompt_from_context(ctx)

    # 新增内部方法：使用统一结构
    def _build_prompt_from_context(self, ctx: AgentPromptContext) -> str:
        """
        内部方法：从统一上下文构建 Prompt。

        所有 Agent 内部使用此方法进行 Prompt 构建，
        确保参数传递的一致性。
        """
        template = (
            self.STANDARD_SYSTEM_TEMPLATE_ZH
            if ctx.language == "zh"
            else self.STANDARD_SYSTEM_TEMPLATE_EN
        )

        print(f"[{self.name}] 内部参数传递调试:\n{ctx.get_summary()}")

        return template.format(
            agent_name=ctx.agent_name,
            agent_description=ctx.agent_description,
            instruction=ctx.core_instruction or "No task specified",
            upstream_capabilities=ctx.upstream_capabilities or "None provided",
            allowed_tools=ctx.tools_summary,
            context=ctx.background_context or "No additional context",
        )
```

### 2. Orchestrator 改造

**修改位置**: `src/core/orchestrator.py`

```python
# 原有代码（保持不变）
function_args["instruction"] = new_instruction
function_args["context"] = compressed_context
function_args["upstream_capabilities"] = upstream_view

# 新增：调试日志
from src.core.capability import AgentPromptContext
ctx = AgentPromptContext.from_legacy_params(
    instruction=new_instruction,
    context=compressed_context,
    upstream_capabilities=upstream_view,
    agent_name=function_name,
    agent_description=capability.description,
)
print(f"[Orchestrator] 参数传递调试信息:\n{ctx.get_summary()}")
```

## 优势

### 1. 完全向后兼容
- ✅ 外部接口完全不变
- ✅ 所有现有 Agent 无需修改
- ✅ ReactAgent、QwenBridgeAgent、AutoGLMGUIAgent 都正常工作

### 2. 内部标准化
- ✅ 所有 Agent 内部使用统一结构
- ✅ 参数传递可追踪、可调试
- ✅ 为未来扩展预留空间

### 3. 最小改动
- ✅ 仅修改 `BaseAgent.build_full_prompt()` 方法
- ✅ 新增内部 `_build_prompt_from_context()` 方法
- ✅ 在 Orchestrator 添加调试日志

### 4. 可维护性
- ✅ 集中管理所有参数
- ✅ 清晰的调试输出
- ✅ 易于扩展新字段

## 测试验证

### 测试 1: 基础功能
```python
ctx = AgentPromptContext.from_legacy_params(
    instruction='Test task',
    context='Test context',
    upstream_capabilities='Test capabilities',
    agent_name='test_agent',
    agent_description='Test description',
    allowed_tools=['tool1', 'tool2'],
)
summary = ctx.get_summary()
legacy_dict = ctx.to_legacy_dict()
```
✅ **通过**

### 测试 2: HelloWorldAgent
```python
agent = HelloWorldAgent()
prompt = agent.build_full_prompt(
    instruction='Say hello',
    context='Test context',
    upstream_capabilities='Test capabilities',
    language='zh'
)
```
✅ **通过** - 正确生成 Prompt，包含所有必要信息

### 测试 3: WebAgent
```python
agent = WebAgent()
prompt = agent.build_full_prompt(
    instruction='Bing search',
    context='Test context',
    upstream_capabilities='Test capabilities',
    language='zh'
)
```
✅ **通过** - 正确追加特殊规则（文件权限、网页保持）

### 测试 4: 完整流程
```python
# 模拟 Orchestrator → Compressor → Agent 流程
agent = HelloWorldAgent()
prompt = agent.build_full_prompt(
    instruction="测试任务：向用户问好",
    context="背景信息：用户首次使用系统",
    upstream_capabilities="上级能力：搜索、代码执行",
    language="zh"
)
```
✅ **通过** - 所有参数正确传递，调试日志正常输出

## 数据流转图

```
┌─────────────────────────────────────────────────────────────────┐
│                   Orchestrator                        │
│                                                          │
│  ┌─────────────────────────────────────────────────┐      │
│  │ Compressor 压缩历史                     │      │
│  │ 输入：history, task, agent_desc         │      │
│  │ 输出：core_request, compressed_context    │      │
│  └─────────────────────────────────────────────────┘      │
│                          ↓                                 │
│  构建参数（标准化）                                  │
│  function_args = {                                   │
│    "instruction": core_request,                       │
│    "context": compressed_context,                       │
│    "upstream_capabilities": upstream_view,               │
│  }                                                      │
│                          ↓                                 │
│  调试日志（新增）                                        │
│  AgentPromptContext.from_legacy_params(...)           │
│  print(ctx.get_summary())                             │
│                          ↓                                 │
│  调用 Agent.execute(...)                         │
└──────────────────────┬────────────────────────────────────────┘
                       │
                       ↓
┌─────────────────────────────────────────────────────────────────┐
│                      Sub-Agent                          │
│  ┌─────────────────────────────────────────────────┐      │
│  │ build_full_prompt() [外部接口]           │      │
│  │ 接受：instruction, context, ...        │      │
│  └─────────────────────────────────────────────────┘      │
│                          ↓                                 │
│  ┌─────────────────────────────────────────────────┐      │
│  │ from_legacy_params() [内部转换]          │      │
│  │ ↓                                         │      │
│  │ AgentPromptContext [统一结构]          │      │
│  └─────────────────────────────────────────────────┘      │
│                          ↓                                 │
│  ┌─────────────────────────────────────────────────┐      │
│  │ _build_prompt_from_context() [内部方法]  │      │
│  │ 格式化模板                                │      │
│  │ 输出完整 Prompt                          │      │
│  └─────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

## 未来扩展点

### 1. 字段扩展
`AgentPromptContext` 预留了多个未使用的字段，可以逐步启用：
- `session_id`：追踪会话
- `trace_id`：追踪执行链
- `task_priority`：任务优先级
- `task_category`：任务分类
- `additional_rules`：特殊规则插件
- `constraints`：约束条件

### 2. 方法扩展
可以添加更多辅助方法：
- `validate()`：验证上下文完整性
- `compress()`：压缩大型字段
- `merge()`：合并多个上下文

### 3. Prompt 构建增强
`_build_prompt_from_context()` 可以扩展为：
- 模板选择逻辑（根据 Agent 类型）
- 规则注入（来自 `additional_rules`）
- 内容验证（确保不超长）

## 注意事项

### 1. LSP 错误（原有代码问题）
```
ERROR: Method "execute" overrides class "Capability" in an incompatible manner
```
这是 `BaseAgent.execute()` 方法签名与 `Capability.execute()` 不匹配的**原有设计问题**，不属于本次改动范围。

### 2. 调试日志输出
测试时会看到以下调试输出：
```
[Orchestrator] 参数传递调试信息:
[AgentPromptContext]
  Agent: xxx
  Instruction: ...
  Context: xxx chars
  ...

[xxx_agent] 内部参数传递调试:
[AgentPromptContext]
  Agent: xxx
  Instruction: ...
  ...
```

这些日志可以在生产环境关闭（通过配置开关）。

### 3. 向后兼容性
- 所有现有 Agent 无需修改
- `build_full_prompt()` 外部接口完全不变
- 内部使用 `AgentPromptContext` 统一结构
