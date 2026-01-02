from src.core.capability import BaseTool

class GreetingTool(BaseTool):
    name = "greeting_tool"
    description = "Generates a formal greeting message with a verification timestamp."
    parameters = {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the person to greet"}
        },
        "required": ["name"]
    }

    async def execute(self, name: str) -> str:
        import datetime
        timestamp = datetime.datetime.now().isoformat()
        return f"Hello, {name}! Your presence has been verified at {timestamp} by OneAgent System."
