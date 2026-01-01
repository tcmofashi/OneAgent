import importlib
import inspect
import sys
from pathlib import Path

from src.core.registry import global_registry
from src.core.capability import BaseAgent
from src.capabilities.tools.system_info import SystemInfoTool

from src.core.capability import BaseTool

def load_capabilities():
    """
    加载所有能力 (Agents, Tools) 到注册表。
    Load all capabilities (Agents, Tools) into the registry.
    """
    # 1. Register Global Shared Tools
    global_registry.register(SystemInfoTool())
    
    # 2. Load Directory-Based Agents
    agents_root = Path(__file__).parent.parent / "capabilities" / "agents"
    if not agents_root.exists():
        print(f"[Loader] Agents root not found: {agents_root}")
        return

    sys.path.append(str(agents_root.parent)) # Ensure capabilities package is importable

    for agent_dir in agents_root.iterdir():
        if agent_dir.is_dir() and (agent_dir / "agent.py").exists():
            try:
                # Dynamic import: src.capabilities.agents.[agent_name].agent
                module_name = f"src.capabilities.agents.{agent_dir.name}.agent"
                module = importlib.import_module(module_name)
                
                # Find BaseAgent subclass
                for name, obj in inspect.getmembers(module):
                    if inspect.isclass(obj) and issubclass(obj, BaseAgent) and obj is not BaseAgent:
                        print(f"[Loader] Found Agent class: {name} in {agent_dir.name}")
                        agent_instance = obj()
                        
                        # --- Load Scoped Tools ---
                        tools_dir = agent_dir / "tools"
                        if tools_dir.exists():
                            # Add tools dir to path so we can import from it
                            # sys.path.append(str(tools_dir)) # Optional if we use relative import
                            for tool_file in tools_dir.glob("*.py"):
                                if tool_file.name == "__init__.py": continue
                                
                                try:
                                    tool_module_name = f"src.capabilities.agents.{agent_dir.name}.tools.{tool_file.stem}"
                                    tool_module = importlib.import_module(tool_module_name)
                                    
                                    for t_name, t_obj in inspect.getmembers(tool_module):
                                        if inspect.isclass(t_obj) and issubclass(t_obj, BaseTool) and t_obj is not BaseTool:
                                            print(f"  [Loader] Found Scoped Tool: {t_name}")
                                            tool_instance = t_obj()
                                            
                                            # Register globally but typically this tool is specific to this agent
                                            # To avoid collision, we might want to namespacify it if needed, 
                                            # but for now we register as is and whitelist it.
                                            global_registry.register(tool_instance)
                                            agent_instance.allowed_tools.append(tool_instance.name)
                                except Exception as e:
                                    print(f"  [Loader] Failed to load tool {tool_file.name}: {e}")

                        # --- Load Scoped MCP ---
                        mcp_config_path = agent_dir / "mcp.toml"
                        if mcp_config_path.exists():
                            import toml
                            try:
                                with open(mcp_config_path, "r", encoding="utf-8") as f:
                                    mcp_data = toml.load(f)
                                    # We attach the config to the agent instance for later use
                                    agent_instance.mcp_config = mcp_data
                                    print(f"  [Loader] Loaded MCP config for {agent_instance.name}")
                            except Exception as e:
                                print(f"  [Loader] Failed to load MCP config: {e}")
                        
                        global_registry.register(agent_instance)
            except Exception as e:
                print(f"[Loader] Failed to load agent from {agent_dir.name}: {e}")
