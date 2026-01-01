import platform
import os
from src.core.capability import BaseTool

class SystemInfoTool(BaseTool):
    name = "get_system_info"
    description = "Get basic information about the current system (OS, Python version, etc)."
    parameters = {
        "type": "object",
        "properties": {} # No parameters needed
    }

    async def execute(self, **kwargs) -> str:
        info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "python_version": platform.python_version(),
            "cwd": os.getcwd()
        }
        return str(info)
