"""
Request User Input Tool - 请求用户输入或等待用户操作

用于 Orchestrator 在需要用户参与时暂停执行：
- 请求用户提供额外信息
- 等待用户完成某个手动操作后继续
"""
from src.core.capability import BaseTool


class RequestUserInputTool(BaseTool):
    name = "request_user_input"
    description = """Request input from the user or wait for the user to complete a task.
Use this when you need:
1. Additional information from the user to proceed
2. User to perform a manual action (e.g., deploy, restart a service)
3. User confirmation before proceeding with a critical operation"""
    
    parameters = {
        "type": "object",
        "properties": {
            "prompt": {
                "type": "string",
                "description": "The message to display to the user, explaining what input is needed or what action they should perform."
            },
            "wait_for_action": {
                "type": "boolean",
                "description": "If true, wait for user to press any key to continue. If false, wait for user text input.",
                "default": False
            }
        },
        "required": ["prompt"]
    }

    async def execute(self, prompt: str, wait_for_action: bool = False) -> str:
        """
        显示提示并等待用户输入或操作。
        Display prompt and wait for user input or action.
        """
        print(f"\n{'='*60}")
        print(f"🔔 [需要用户输入]")
        print(f"{'='*60}")
        print(f"\n{prompt}\n")
        
        if wait_for_action:
            print(">>> 完成后请按 Enter 键继续...")
            input()
            return "[USER_ACTION_COMPLETED] 用户已确认完成操作"
        else:
            print(">>> 请输入您的回复: ")
            user_input = input()
            return f"[USER_INPUT] {user_input}"
