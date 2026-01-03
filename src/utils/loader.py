import importlib
import inspect
import sys
from pathlib import Path
from typing import Optional

from src.core.registry import global_registry
from src.core.capability import BaseAgent
from src.capabilities.tools.system_info import SystemInfoTool
from src.capabilities.tools.request_user_input import RequestUserInputTool
from src.core.config import global_config

from src.core.capability import BaseTool


def _should_load_agent(agent_name: str, mode: str, whitelist: Optional[list], blacklist: Optional[list]) -> bool:
    """
    判断是否应该加载指定的 agent
    
    Args:
        agent_name: Agent 目录名
        mode: 加载模式 ("all", "whitelist", "blacklist")
        whitelist: 白名单列表
        blacklist: 黑名单列表
    
    Returns:
        True 如果应该加载该 agent
    """
    if mode == "all":
        return True
    elif mode == "whitelist":
        return whitelist is not None and agent_name in whitelist
    elif mode == "blacklist":
        return blacklist is None or agent_name not in blacklist
    else:
        # 未知模式，默认加载
        print(f"[Loader] Warning: Unknown capabilities mode '{mode}', defaulting to 'all'")
        return True


def load_capabilities():
    """
    加载所有能力 (Agents, Tools) 到注册表。
    Load all capabilities (Agents, Tools) into the registry.
    
    支持通过 config.toml 的 [capabilities] 节控制加载的 agents：
    - mode = "all": 加载所有（默认）
    - mode = "whitelist": 仅加载 whitelist 列表中的 agents
    - mode = "blacklist": 排除 blacklist 列表中的 agents
    """
    # 读取配置
    capabilities_mode = global_config.get("capabilities.mode") or "all"
    capabilities_whitelist = global_config.get("capabilities.whitelist")
    capabilities_blacklist = global_config.get("capabilities.blacklist")
    mcp_enabled = global_config.get("capabilities.mcp.enabled")
    if mcp_enabled is None:
        mcp_enabled = True  # 默认启用 MCP
    mcp_blacklist = global_config.get("capabilities.mcp.blacklist") or []
    
    print(f"[Loader] Capabilities mode: {capabilities_mode}")
    
    # 1. Register Global Shared Tools (available to Orchestrator)
    global_registry.register(SystemInfoTool())
    global_registry.register(RequestUserInputTool())
    
    # 2. Register Runtime Tools (standard sub-agent tools, excluded from Orchestrator)
    from src.runtime_tools.report_status import ReportStatusTool
    global_registry.register(ReportStatusTool(), is_runtime_tool=True)

    
    # 3. Load Directory-Based Agents
    agents_root = Path(__file__).parent.parent / "capabilities" / "agents"
    if not agents_root.exists():
        print(f"[Loader] Agents root not found: {agents_root}")
        return

    sys.path.append(str(agents_root.parent)) # Ensure capabilities package is importable

    for agent_dir in agents_root.iterdir():
        if agent_dir.is_dir() and (agent_dir / "agent.py").exists():
            agent_dir_name = agent_dir.name
            
            # 检查是否应该加载此 agent
            if not _should_load_agent(agent_dir_name, capabilities_mode, capabilities_whitelist, capabilities_blacklist):
                print(f"[Loader] Skipping agent: {agent_dir_name} (filtered by {capabilities_mode} mode)")
                continue
            
            try:
                # Dynamic import: src.capabilities.agents.[agent_name].agent
                module_name = f"src.capabilities.agents.{agent_dir_name}.agent"
                module = importlib.import_module(module_name)
                
                # Find BaseAgent subclass defined in THIS module (not imported)
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) 
                        and issubclass(obj, BaseAgent) 
                        and obj is not BaseAgent
                        and obj.__module__ == module.__name__):  # 确保是在此模块定义的类
                        print(f"[Loader] Found Agent class: {name} in {agent_dir_name}")
                        agent_instance = obj()
                        
                        # --- Load Scoped Tools ---
                        tools_dir = agent_dir / "tools"
                        if tools_dir.exists():
                            for tool_file in tools_dir.glob("*.py"):
                                if tool_file.name == "__init__.py":
                                    continue
                                
                                try:
                                    tool_module_name = f"src.capabilities.agents.{agent_dir_name}.tools.{tool_file.stem}"
                                    tool_module = importlib.import_module(tool_module_name)
                                    
                                    for t_name, t_obj in inspect.getmembers(tool_module):
                                        if inspect.isclass(t_obj) and issubclass(t_obj, BaseTool) and t_obj is not BaseTool:
                                            print(f"  [Loader] Found Scoped Tool: {t_name}")
                                            tool_instance = t_obj()
                                            
                                            global_registry.register(tool_instance)
                                            agent_instance.allowed_tools.append(tool_instance.name)
                                except Exception as e:
                                    print(f"  [Loader] Failed to load tool {tool_file.name}: {e}")

                        # --- Load Scoped MCP ---
                        if mcp_enabled:
                            mcp_config_path = agent_dir / "mcp.toml"
                            if mcp_config_path.exists():
                                import toml
                                try:
                                    with open(mcp_config_path, "r", encoding="utf-8") as f:
                                        mcp_data = toml.load(f)
                                        
                                        # 过滤 MCP 黑名单
                                        if mcp_blacklist and "servers" in mcp_data:
                                            filtered_servers = {
                                                k: v for k, v in mcp_data.get("servers", {}).items()
                                                if k not in mcp_blacklist
                                            }
                                            mcp_data["servers"] = filtered_servers
                                        
                                        agent_instance.mcp_config = mcp_data
                                        print(f"  [Loader] Loaded MCP config for {agent_instance.name}")
                                except Exception as e:
                                    print(f"  [Loader] Failed to load MCP config: {e}")
                        
                        global_registry.register(agent_instance)
            except Exception as e:
                print(f"[Loader] Failed to load agent from {agent_dir_name}: {e}")
