from src.core.capability import BaseTool

class SampleScopedTool(BaseTool):
    name = "sample_scoped_tool"
    description = "A tool that is specific to SampleAgent."
    parameters = {
        "type": "object",
        "properties": {
            "msg": {"type": "string", "description": "Message to print"}
        },
        "required": ["msg"]
    }

    async def execute(self, msg: str) -> str:
        return f"[SampleScopedTool] Echo: {msg}"
