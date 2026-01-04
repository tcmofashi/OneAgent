from src.core.capability import BaseTool
from typing import Dict, Any

class UpdateAgentTasksTool(BaseTool):
    name = "update_agent_tasks"
    description = "Update the persistent Agent Task Allocation List. Use this to track tasks delegated to sub-agents. Update this list before delegating a task or when a sub-agent completes a task."
    parameters = {
        "type": "object",
        "properties": {
            "agent_tasks": {
                "type": "string",
                "description": "The full content of the Agent Task List in Markdown format (e.g., - [ ] WebAgent: Search for 'foo'\n- [x] CodeAgent: Refactor 'bar')."
            }
        },
        "required": ["agent_tasks"]
    }

    def __init__(self, orchestrator_ref):
        self.orchestrator = orchestrator_ref

    async def execute(self, **kwargs) -> str:
        # 灵活参数处理：接受多种可能的参数名
        agent_tasks = (
            kwargs.get("agent_tasks") or 
            kwargs.get("task_list") or 
            kwargs.get("tasks") or
            kwargs.get("content") or
            kwargs.get("list") or
            ""
        )
        
        if not agent_tasks:
            return "[FAILURE] Missing required parameter: agent_tasks. Please provide the task list content."
        
        self.orchestrator.update_agent_tasks(agent_tasks)
        return "Agent Task Allocation List updated successfully."
