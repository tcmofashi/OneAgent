import asyncio
import json
import sys
import os

# Set up path
sys.path.insert(0, os.path.abspath("/home/tcmofashi/proj/OneAgent"))

from src.core.registry import global_registry
from src.core.registry import global_registry
from src.utils.loader import load_capabilities
from src.core.config import global_config

async def main():
    print("Initializing Registry...")
    # Load configuration
    # Force blacklist mode like the user
    # Note: Global config is singleton, modifying it affects the loader
    # but we need to ensure we don't accidentally load everything if config file says otherwise
    # However, since we are reading from file in main app, here we rely on what global_config loads
    # or override it.
    
    global_config.config_data["capabilities"] = {
        "mode": "blacklist",
        "blacklist": ["autoglm_gui_agent"],
        "mcp": {"enabled": True}
    }
    
    load_capabilities()
    
    print("\nAllowed Tools:")
    tools = global_registry.get_all_tool_schemas(exclude_runtime_tools=True)
    
    found = False
    for tool in tools:
        print(f"- {tool['function']['name']}")
        if tool['function']['name'] == 'gui_automation_agent':
            found = True
            print("\nSchema for gui_automation_agent:")
            print(json.dumps(tool, indent=2, ensure_ascii=False))
            
    if not found:
        print("\nERROR: gui_automation_agent not found in tools!")
        
    print("\nCapabilities Tree String:")
    print(global_registry.get_capabilities_tree_string())

if __name__ == "__main__":
    asyncio.run(main())
