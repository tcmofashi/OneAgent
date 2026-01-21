# 系统信息功能集成文档

## 概述

为所有 OneAgent 代理（RootOneAgent 和 SubOneAgent）添加自动系统信息功能。当代理作为子代理被调用时，其描述中会自动包含本机的基础信息，包括主机名、IP地址、操作系统、Python版本等。

## 背景

在分布式多代理系统中，了解每个子代理运行的机器环境对于调试、监控和决策非常重要。系统信息功能让父代理能够：
- 识别子代理运行在哪个主机上
- 了解系统架构和版本
- 确认 Python 环境兼容性
- 进行负载分配和资源规划

## 功能特性

### 自动信息收集

所有代理在初始化时自动收集以下信息：
- **主机名**: `hostname` - 机器标识
- **IP地址**: `ip_address` - 网络地址
- **操作系统**: `system` 和 `release` - 系统类型和版本
- **平台**: `platform` - 完整平台信息
- **架构**: `machine` - CPU架构（x86_64, arm64等）
- **Python版本**: `python_version` - 运行时Python版本

### 集成方式

信息自动追加到代理的 `description` 字段，格式为：

```
<原始描述>

系统信息:
Host: <hostname> (<ip_address>)
System: <system> <release> (<machine>)
Platform: <platform>
Python: <python_version>
```

## 修改文件清单

### 新增文件

1. **`src/utils/system_info.py`**
   - `get_system_info()` - 获取完整系统信息字典
   - `get_local_ip()` - 获取本机IP地址
   - `format_system_info_for_description()` - 格式化系统信息为字符串

### 修改文件

1. **`src/core/root_one_agent.py`**
   - 导入 `format_system_info_for_description`
   - 在 `__init__` 中自动将系统信息追加到 `description`

2. **`src/core/sub_one_agent.py`**
   - 导入 `format_system_info_for_description`
   - 在 `__init__` 中自动将系统信息追加到 `description`
   - 移除未使用的导入和变量

3. **`tests/test_root_one_agent.py`**
   - 更新 `test_root_one_agent_initialization` 测试
   - 检查描述中是否包含系统信息

4. **`tests/test_sub_one_agent.py`**
   - 更新 `test_sub_one_agent_initialization` 测试
   - 检查描述中是否包含系统信息

## 使用示例

### 创建 RootOneAgent

```python
from src.core.root_one_agent import RootOneAgent

root_agent = RootOneAgent(
    name="MyRootAgent",
    description="负责协调子代理"
)

print(root_agent.description)
```

输出示例：
```
负责协调子代理

系统信息:
Host: myserver (10.42.0.1)
System: Linux 5.15.0-164-generic (x86_64)
Platform: Linux-5.15.0-164-generic-x86_64-with-glibc2.35
Python: 3.9.23
```

### 创建 SubOneAgent

```python
from src.core.sub_one_agent import SubOneAgent

sub_agent = SubOneAgent(
    name="MySubAgent",
    description="负责代码分析"
)

print(sub_agent.description)
```

输出示例：
```
负责代码分析

系统信息:
Host: myserver (10.42.0.1)
System: Linux 5.15.0-164-generic (x86_64)
Platform: Linux-5.15.0-164-generic-x86_64-with-glibc2.35
Python: 3.9.23
```

### 自定义描述

```python
agent = RootOneAgent(
    name="CustomAgent",
    description="这是自定义的代理描述"
)
```

系统信息会自动追加到自定义描述后面。

## 技术实现细节

### IP地址获取

使用 UDP socket 技巧获取本机 IP：
```python
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(0)
s.connect(("8.8.8.8", 80))
ip = s.getsockname()[0]
s.close()
```

此方法的优点：
- 不需要外部依赖
- 能获取实际对外 IP（而非 127.0.0.1）
- 失败时回退到 127.0.0.1

### 系统信息来源

使用 Python 标准库 `platform` 模块：
- `socket.gethostname()` - 主机名
- `platform.system()` - 系统名称
- `platform.release()` - 系统版本
- `platform.machine()` - 机器架构
- `platform.python_version()` - Python 版本

### 格式化策略

系统信息格式化为多行字符串，便于在 LLM 提示词中展示。使用换行符和冒号分隔，保持可读性。

## 测试验证

### 运行单元测试

```bash
PYTHONPATH=/home/tcmofashi/proj/OneAgent pytest tests/test_root_one_agent.py tests/test_sub_one_agent.py -v
```

预期结果：所有测试通过

### 验证系统信息

```bash
PYTHONPATH=/home/tcmofashi/proj/OneAgent python -c "
from src.core.root_one_agent import RootOneAgent
root = RootOneAgent()
print(root.description)
"
```

预期输出：包含"系统信息:"和具体的主机、IP、系统等字段

### 完整测试套件

```bash
PYTHONPATH=/home/tcmofashi/proj/OneAgent pytest tests/ --tb=no -q
```

预期结果：59/59 测试通过

## 影响范围

### 向后兼容性

✅ **完全向后兼容**
- 代理的 `name`、`id` 等属性保持不变
- 系统信息仅追加到 `description` 字段
- 不影响现有 API 和调用方式
- 不破坏现有测试

### 性能影响

✅ **性能影响可忽略**
- 系统信息收集仅在初始化时执行一次
- 使用标准库，无外部依赖
- IP获取使用 UDP socket，无需网络请求（超时设置为 0）

## 故障排查

### IP地址显示为 "unknown"

原因：socket连接失败
解决：代码会回退到 127.0.0.1，不影响功能

### 主机名为空

原因：系统配置问题
解决：检查系统hostname设置（`hostname` 命令）

### Python版本显示不正确

原因：使用了错误的Python解释器运行
解决：确认使用项目虚拟环境中的Python

## 未来扩展

可能的增强方向：
1. **环境变量**：包含关键环境变量
2. **资源限制**：CPU核心数、内存大小
3. **磁盘信息**：可用磁盘空间
4. **网络接口**：所有网络接口列表
5. **时区信息**：系统时区设置
6. **GPU信息**：NVIDIA/AMD GPU检测（如果可用）

## 相关文档

- `docs/oneagent_nested_architecture_design.md` - 嵌套OneAgent架构设计
- `tests/README.md` - 测试指南

## 版本历史

| 版本 | 日期 | 修改内容 | 作者 |
|------|------|---------|------|
| 1.0 | 2025-01-20 | 初始实现：添加系统信息功能到RootOneAgent和SubOneAgent | Sisyphus |
