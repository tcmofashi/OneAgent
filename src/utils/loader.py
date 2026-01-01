import importlib
import inspect
import sys
from pathlib import Path

from src.core.registry import global_registry
from src.core.capability import BaseAgent
from src.capabilities.tools.system_info import SystemInfoTool

def load_capabilities():
    """
    Load all capabilities (Agents, Tools) into the registry.
    """
    # 1. Register Global Shared Tools
    global_registry.register(SystemInfoTool())
    
    # 2. Load Directory-Based Agents
    agents_root = Path(__file__).parent.parent / "capabilities" / "agents"
    if not agents_root.exists():
        print(f"[Loader] Agents root not found: {agents_root}")
        return

    sys.path.append(str(agents_root.parent)) # Ensure capabilities package is importable if needed

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
                        
                        # TODO: Load Scoped Tools from agent_dir/tools
                        # TODO: Load Scoped MCP from agent_dir/mcp.toml
                        
                        global_registry.register(agent_instance)
            except Exception as e:
                print(f"[Loader] Failed to load agent from {agent_dir.name}: {e}")
