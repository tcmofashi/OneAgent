# Qwen Code CLI Agent 能力树

## 概述

Qwen Code CLI 是一个功能强大的命令行编程代理工具，通过 `QwenBridgeAgent` 集成到 OneAgent 框架中。它具有完整的软件开发能力，包括代码编辑、命令行操作、Web 搜索和 MCP 工具扩展。

## 能力树结构

```
qwen_bridge_agent
├── 📝 代码编辑能力
│   ├── 文件读取 (view_file, read_file)
│   ├── 文件创建 (write_to_file)
│   ├── 文件编辑 (replace_file_content, multi_replace_file_content)
│   ├── 文件搜索 (find_by_name, grep_search)
│   └── 代码大纲 (view_file_outline, view_code_item)
│
├── 💻 命令行能力
│   ├── 命令执行 (run_command)
│   │   ├── 同步执行: 短命令同步等待结果
│   │   ├── 异步执行: 长时间后台任务
│   │   └── 交互输入: send_command_input
│   ├── 命令状态查询 (command_status)
│   └── 平台工具
│       ├── Linux: bash, git, npm, pip, docker, curl, wget, make, gcc, python3...
│       ├── macOS: bash, zsh, brew, git, npm, pip, xcode-build...
│       └── Windows: cmd, powershell, git, npm, pip, winget...
│
├── 🌐 Web 搜索能力
│   ├── 搜索引擎 (search_web)
│   │   ├── Dashscope (默认)
│   │   ├── Tavily (--tavily-api-key)
│   │   └── Google Custom Search (--google-api-key)
│   └── URL 内容读取 (read_url_content)
│
├── 🔌 MCP 扩展能力
│   ├── MCP 服务器连接 (--allowed-mcp-server-names)
│   ├── 自定义工具注入 (--core-tools)
│   └── 工具过滤 (--exclude-tools, --allowed-tools)
│
├── 📦 工作区管理
│   ├── 目录列表 (list_dir)
│   ├── 工作区扫描
│   ├── gitignore 感知
│   └── 多目录包含 (--include-directories)
│
├── 🖼️ 多模态能力
│   ├── 图像识别 (VLM 模式)
│   │   └── --vlm-switch-mode: once/session/persist
│   ├── 图像生成 (generate_image)
│   └── 屏幕截图理解
│
├── 🧪 沙箱执行
│   ├── Docker 沙箱 (--sandbox)
│   ├── macOS Sandbox Profile
│   └── 隔离环境配置 (--sandbox-image)
│
├── 🔐 认证方式
│   ├── OpenAI Compatible (--auth-type openai)
│   ├── Anthropic (--auth-type anthropic)
│   ├── Qwen OAuth (--auth-type qwen-oauth)
│   └── Gemini/Vertex AI
│
└── 📊 会话管理
    ├── 会话恢复 (--continue, --resume)
    ├── 历史记录 (--chat-recording)
    └── 检查点 (--checkpointing)
```

## 详细能力说明

### 📝 代码编辑能力

| 工具名称                     | 功能描述                   | 使用示例                       |
| ---------------------------- | -------------------------- | ------------------------------ |
| `view_file`                  | 查看文件内容（支持行范围） | 查看 `src/main.py` 第 10-50 行 |
| `write_to_file`              | 创建新文件或覆盖现有文件   | 创建 `utils/helper.py`         |
| `replace_file_content`       | 单块替换文件内容           | 修复函数中的 bug               |
| `multi_replace_file_content` | 多块非连续替换             | 批量重命名变量                 |
| `find_by_name`               | 按文件名/目录名搜索        | 查找所有 `*.py` 文件           |
| `grep_search`                | 按内容搜索文件             | 搜索所有包含 `TODO` 的文件     |
| `view_file_outline`          | 查看文件代码大纲           | 获取类和函数定义               |

### 💻 命令行能力

Qwen CLI 具有完整的系统命令执行能力，能够调用当前平台的所有命令行工具：

**Linux 平台常用工具：**
```bash
# 包管理
apt, yum, dnf, pacman, pip, npm, cargo

# 开发工具
git, make, cmake, gcc, g++, python3, node, go

# 系统工具
ls, cat, grep, sed, awk, find, xargs, curl, wget

# 容器/虚拟化
docker, podman, kubectl, vagrant

# 文件操作
cp, mv, rm, mkdir, chmod, chown, tar, zip
```

**macOS 平台常用工具：**
```bash
# 包管理
brew, pip, npm, cargo

# 开发工具
xcode-select, swift, clang, python3, node

# 系统工具
pbcopy, pbpaste, open, defaults, launchctl
```

**Windows 平台常用工具：**
```powershell
# 包管理
winget, choco, scoop, pip, npm

# 开发工具  
git, python, node, dotnet, cargo

# 系统工具
Get-ChildItem, Copy-Item, Move-Item, Remove-Item
```

### 🌐 Web 搜索能力

| 提供商    | 配置方式                                         | 特点              |
| --------- | ------------------------------------------------ | ----------------- |
| Dashscope | 默认启用                                         | 阿里云搜索服务    |
| Tavily    | `--tavily-api-key`                               | 优化的 AI 搜索    |
| Google    | `--google-api-key` + `--google-search-engine-id` | Google 自定义搜索 |

### 🔐 工作模式

| 模式        | 描述               | 适用场景       |
| ----------- | ------------------ | -------------- |
| `plan`      | 仅生成计划，不执行 | 预览变更       |
| `default`   | 每次操作需用户确认 | 安全的交互模式 |
| `auto-edit` | 自动批准编辑操作   | 信任代码修改   |
| `yolo`      | 自动批准所有操作   | 完全自动化     |

## OneAgent 协议集成

### 输入格式

作为 OneAgent 子代理时，接收标准化输入：

```python
{
    "instruction": "具体任务描述",
    "context": "压缩后的相关上下文",
    "upstream_capabilities": "可申请的上级能力列表"
}
```

### 状态报告

通过 `report_status` 工具向 Orchestrator 报告状态：

| 状态          | 含义                   | 后续动作                     |
| ------------- | ---------------------- | ---------------------------- |
| `SUCCESS`     | 任务成功完成           | 继续下一任务                 |
| `FAILURE`     | 执行失败（客观原因）   | 可能重试或跳过               |
| `REJECTED`    | 拒绝执行（任务不合理） | 重新路由                     |
| `INTERRUPTED` | 需要上级协助           | 等待 Orchestrator 处理后继续 |

### 输出格式

实时流式输出，支持多种消息类型：

```
💭 思考: [Agent 推理过程]
🔧 调用工具: [工具名称和参数]
📋 工具结果: [执行结果摘要]
✅ 状态报告: [SUCCESS/FAILURE/REJECTED/INTERRUPTED]
🏁 完成: [耗时和轮次统计]
```

## 配置示例

### config.toml 模型配置

```toml
[llm]
active_provider = "siliconflow"

[llm.functional_roles]
code_generation = "qwen-coder"  # 指定代码生成使用的模型

[llm.models]
qwen-coder = { provider = "siliconflow", model_name = "Qwen/Qwen2.5-Coder-32B-Instruct" }
```

### 环境变量

| 变量                     | 描述         |
| ------------------------ | ------------ |
| `OPENAI_API_KEY`         | API 密钥     |
| `OPENAI_BASE_URL`        | API 端点 URL |
| `QWEN_DISABLE_TELEMETRY` | 禁用遥测     |

## 使用限制

1. **文件系统**：仅能访问工作区内的文件
2. **网络**：需配置相应 API Key 才能使用 Web 搜索
3. **上级能力**：需通过 `INTERRUPTED` 状态申请 Orchestrator 的工具

---

**版本**: 2.0.0  
**最后更新**: 2026年1月4日  
**维护者**: OneAgent 开发团队