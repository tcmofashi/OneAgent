# GUI Automation Agent

基于 [gelab-zero](https://github.com/stepfun-ai/gelab-zero) 封装的 GUI 自动化子 Agent。

## 功能

通过 ADB 控制安卓设备执行 GUI 自动化任务：
- 点击、输入、滑动等基本操作
- 应用唤醒和切换
- 人机交互确认（INFO 动作）

## 环境准备

> **注意**：本项目使用 **UV** 进行环境管理

### 1. 安装依赖

```bash
# 使用 UV（推荐）
cd /path/to/OneAgent
uv pip install -r requirements.txt

# 或手动安装 gelab-zero 依赖
uv pip install megfile pyyaml Pillow jsonlines
```

### 2. 安装 gelab-zero 模型

```bash
# 下载并导入模型到 ollama
ollama create gelab-zero-4b-preview -f /path/to/Modelfile
```

### 3. 配置安卓设备

1. 在手机上开启"开发者选项"和"USB 调试"
2. 用 USB 线连接手机到电脑
3. 验证连接：`adb devices`
4. 在 `config.toml` 中配置设备 ID（可选）

## 配置

### 模型配置（config/config.toml）

模型由 OneAgent 主配置统一管理：

```toml
[llm.functional_roles]
gui_automation = "gelab-zero"

[llm.providers.ollama]
api_base = "http://localhost:11434/v1"
api_key = "ollama"

[llm.models]
gelab-zero = { provider = "ollama", model_name = "gelab-zero-4b-preview" }
```

### Agent 配置（本目录 config.toml）

```toml
[agent]
max_steps = 50
delay_after_capture = 2.0

[device]
selection = "first"  # 或 "specify"
# device_id = "YOUR_DEVICE_ID"
```

## 动作映射

| gelab-zero 结果 | OneAgent 状态 |
| --------------- | ------------- |
| COMPLETE        | `success`     |
| ABORT           | `failure`     |
| INFO            | `interrupted` |

## 使用示例

```python
# Orchestrator 调用此 Agent
agent = registry.get_capability("gui_automation_agent")
result = await agent.execute(
    instruction="打开微信，给张三发消息 hello"
)
```
