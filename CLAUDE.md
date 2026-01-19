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
│   ├── runtime_tools/  # 运行时工具（共享内存、文件系统）
│   │   ├── shared_memory.py   # 两级共享内存核心
│   │   ├── memory_io_tools.py # Level 1: 内存 I/O 工具
│   │   └── shared_fs_tools.py # Level 2: 文件系统工具
│   └── capabilities/   # 能力（工具和代理）
└── config/             # 配置文件
```

---

## 两级共享内存系统

OneAgent 为所有子代理提供了两级共享内存系统，支持跨代理的数据共享和持久化存储。

### 系统架构

```
┌───────────────────────────────┐
│  Level 1 (In-Memory)      │
│  4K 环形缓冲区                  │
│  - 线程安全                    │
│  - FIFO 自动清理              │
│  - 高速 I/O（微秒级）           │
└───────────────────────────────┘
            ↓ 所有代理可用
┌───────────────────────────────┐
│  Level 2 (File System)      │
│  .OneAgent/ 目录               │
│  - CRUD 操作                   │
│  - 路径安全验证                │
│  - 持久化存储                  │
└───────────────────────────────┘
```

### Level 1: 4K 内存环形缓冲区

**特性**：
- 容量：4096 条记录（每条记录最大 1KB）
- 线程安全：使用 `threading.Lock` 保护并发访问
- FIFO 行为：写入超过容量时自动删除最早记录
- 单例模式：全局唯一的共享内存实例
- 微秒级响应：纯内存操作，无磁盘 I/O

**可用工具**：

| 工具名称 | 用途 | 参数 |
|---------|------|------|
| `memory_write` | 写入内容到共享内存 | `content`: 文本内容（可选） |
| `memory_read` | 读取共享内存内容 | `lines`: 读取行数（可选，默认全部） |
| `memory_clear` | 清空共享内存 | 无 |
| `memory_info` | 获取内存统计信息 | 无 |

**使用示例**：

```python
# 作为子代理时
await tool_manager.execute_tool("memory_write", content="任务进度: 50%")

await tool_manager.execute_tool("memory_read", lines=10)

await tool_manager.execute_tool("memory_clear")
```

### Level 2: .OneAgent 文件系统

**特性**：
- 目录：项目根目录下的 `.OneAgent/`（已加入 `.gitignore`）
- CRUD 操作：创建、读取、列出、删除文件
- 路径安全：防止目录遍历攻击（`../`）和绝对路径
- 自动创建：写入时自动创建父目录
- 持久化存储：文件保存到磁盘，重启后仍存在

**可用工具**：

| 工具名称 | 用途 | 参数 |
|---------|------|------|
| `shared_save_to_file` | 保存内容到文件 | `path`: 文件路径（相对 .OneAgent/）<br>`content`: 文件内容<br>`mode`: `write` 或 `append` |
| `shared_read_file` | 读取文件内容 | `path`: 文件路径<br>`offset`: 起始偏移（可选）<br>`limit`: 读取行数（可选） |
| `shared_list_files` | 列出目录文件 | `pattern`: glob 模式（如 `**/*.txt`）<br>`path`: 相对路径（可选） |
| `shared_delete_file` | 删除文件 | `path`: 文件路径 |

**使用示例**：

```python
# 保存文件
await tool_manager.execute_tool(
    "shared_save_to_file",
    path="results/output.json",
    content='{"status": "success"}',
    mode="write"
)

# 追加写入
await tool_manager.execute_tool(
    "shared_save_to_file",
    path="logs/agent.log",
    content="[2025-01-19] Task completed\n",
    mode="append"
)

# 读取文件（分页）
await tool_manager.execute_tool(
    "shared_read_file",
    path="results/output.json",
    offset=0,
    limit=100
)

# 列出所有 JSON 文件
await tool_manager.execute_tool(
    "shared_list_files",
    pattern="**/*.json"
)

# 删除文件
await tool_manager.execute_tool(
    "shared_delete_file",
    path="temp/cache.txt"
)
```

### 工具注册与可用性

**工具注册位置**：
- `src/runtime_tools/memory_io_tools.py` - Level 1 内存工具
- `src/runtime_tools/shared_fs_tools.py` - Level 2 文件系统工具
- `src/utils/loader.py` - 工具注册中心

**可用性规则**：
- **所有代理可用**（包括 orchestrator 和子代理）：
  - `memory_write`, `memory_read`, `memory_clear`, `memory_info`
  - `shared_save_to_file`, `shared_read_file`, `shared_list_files`, `shared_delete_file`

**工具加载方式**：
- 工具通过 `src/utils/loader.py` 自动加载
- `is_runtime_tool=True` 标记为运行时工具
- 通过 `get_all_tool_schemas()` 获取所有可用工具

### 安全机制

**路径安全验证**（Level 2）：
- ✅ 允许：相对路径（如 `data/file.txt`）
- ❌ 禁止：绝对路径（如 `/etc/passwd`）
- ❌ 禁止：目录遍历（如 `../config.toml`）
- ✅ 允许：子目录（如 `agent1/results/output.json`）

### 使用场景

**Level 1（内存）适用场景**：
- 代理间临时数据交换
- 任务状态快速同步
- 中间结果缓存
- 日志缓冲（快速写入）

**Level 2（文件系统）适用场景**：
- 大数据持久化存储
- 跨会话数据保留
- 文件输出（报告、日志、图片）
- 结构化数据存储（JSON、CSV、YAML）

---

## 重定向包装器工具（Redirect Wrapper Tools）

OneAgent 提供了重定向包装器工具，允许灵活地将任意工具的输出重定向到文件或共享内存。

### 可用工具

| 工具名称 | 用途 | 何时使用 |
|---------|------|---------|
| `redirect_to_file` | 执行工具并将输出保存到 `.OneAgent/` 文件 | 需要持久化存储工具输出 |
| `redirect_to_mem` | 执行工具并将输出保存到共享内存 | 需要快速存储临时结果 |
| `redirect_to_file_and_mem` | 执行工具并同时保存到文件和内存 | 需要同时持久化和快速访问 |

### 工具参数

所有重定向工具支持以下参数：

| 参数 | 类型 | 必需 | 描述 |
|-----|------|-----|------|
| `tool_name` | string | ✅ | 要执行的工具名称 |
| `tool_params` | dict | ❌ | 传递给工具的参数（默认为 `{}`） |
| `file` | string | `redirect_to_file` 需要 | 文件路径（相对于 `.OneAgent/`） |
| `mode` | string | ❌ | 文件写入模式：`"w"` (覆盖，默认) / `"a"` (追加) |
| `silent` | bool | ❌ | 是否隐藏重定向消息（默认 `False`） |
| `return_original` | bool | ❌ | 是否返回原始输出（默认 `True`） |

### 使用示例

#### 基本文件重定向

```python
# 执行 evaluate_script 工具并保存输出到文件
result = await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="evaluate_script",
    tool_params={"code": "print('Hello, World!')"},
    file="output.txt",
    mode="w"
)
# 返回: "Hello, World!\n\n[Output redirected to file: .OneAgent/output.txt]"
```

#### 追加模式

```python
# 第一次写入
await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="bash_command",
    tool_params={"command": "echo 'First line'"},
    file="log.txt",
    mode="w"
)

# 追加内容
await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="bash_command",
    tool_params={"command": "echo 'Second line'"},
    file="log.txt",
    mode="a"
)
```

#### 静默模式（不显示重定向消息）

```python
# 静默重定向，返回原始输出
result = await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="get_system_info",
    tool_params={},
    file="system_info.json",
    silent=True
)
# 返回: "{'system': 'Linux', ...}" (没有重定向消息)
```

#### 隐藏原始输出（仅返回空字符串）

```python
# 执行工具并保存输出，但返回空字符串
result = await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="evaluate_script",
    tool_params={"code": "print('Sensitive data')"},
    file="sensitive.txt",
    return_original=False
)
# 返回: "" (空字符串)
# 文件 .OneAgent/sensitive.txt 包含 "Sensitive data"
```

#### 重定向到共享内存

```python
# 执行工具并保存到共享内存
result = await tool_manager.execute_tool(
    "redirect_to_mem",
    tool_name="bash_command",
    tool_params={"command": "ps aux | head -5"}
)
# 输出被保存到 Level 1 共享内存（4K 环形缓冲区）
# 其他代理可以通过 memory_read 读取
```

#### 同时重定向到文件和内存

```python
# 同时保存到文件和内存
result = await tool_manager.execute_tool(
    "redirect_to_file_and_mem",
    tool_name="get_system_info",
    file="system_info.txt"
)
# 输出同时保存到 .OneAgent/system_info.txt 和共享内存
```

### 行为说明

#### 链式调用模式

重定向工具采用链式调用模式：
1. **执行工具** - 调用 `tool_name` 指定的工具
2. **处理错误** - 如果工具执行失败，不保存输出，返回错误信息
3. **保存输出** - 将工具输出保存到目标（文件/内存）
4. **返回结果** - 根据参数返回结果

#### 错误处理

- **工具执行失败**：不保存输出，返回错误信息
- **文件保存失败**：返回原始输出 + 错误信息
- **无效工具名称**：返回错误消息 "Error: Tool 'xxx' not found"
- **缺少必需参数**：返回错误消息

#### return_original 参数控制

| `return_original` | 返回值 | 使用场景 |
|------------------|--------|---------|
| `True` (默认) | 原始输出 + 重定向消息 | 正常查看结果 |
| `False` | 空字符串 `""` | 需要隐藏敏感输出或降低 token 使用量 |

#### silent 参数控制

| `silent` | 返回值 | 使用场景 |
|----------|--------|---------|
| `False` (默认) | 原始输出 + 重定向消息 | 正常查看结果 |
| `True` | 仅原始输出 | 需要干净的输出，不显示重定向提示 |

### 高级用法示例

#### 多步骤数据处理管道

```python
# 1. 执行数据处理并保存临时结果
await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="evaluate_script",
    tool_params={"code": "data = [1,2,3]; print(sum(data))"},
    file="step1.txt",
    silent=True,
    return_original=False
)

# 2. 读取临时结果
step1_result = await tool_manager.execute_tool(
    "shared_read_file",
    filename="step1.txt"
)

# 3. 基于第一步结果执行第二步
final_result = await tool_manager.execute_tool(
    "redirect_to_file",
    tool_name="evaluate_script",
    tool_params={"code": f"print({step1_result} * 2)"},
    file="final_result.txt"
)
```

#### 跨代理数据共享

```python
# Agent A: 计算并保存到共享内存
await tool_manager.execute_tool(
    "redirect_to_mem",
    tool_name="bash_command",
    tool_params={"command": "echo 'Agent A processed data'"},
    silent=True
)

# Agent B: 读取 Agent A 的数据
shared_data = await tool_manager.execute_tool("memory_read")
```

### 注意事项

1. **文件路径**：`file` 参数是相对于 `.OneAgent/` 目录的路径
2. **目录创建**：如果父目录不存在，会自动创建
3. **内存限制**：共享内存是 4K 环形缓冲区，超过容量会自动清理旧数据
4. **并发安全**：共享内存是线程安全的，但文件系统工具不是
5. **权限**：所有代理都可以使用重定向工具，但只能访问 `.OneAgent/` 目录内的文件
