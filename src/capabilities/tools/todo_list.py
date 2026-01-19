from src.core.capability import BaseTool


class TodoListTool(BaseTool):
    name = "update_task_list"
    description = "Update the persistent task list (Todo List). Use this to keep track of your progress. ALWAYS update this when a task is completed or new tasks are discovered."
    parameters = {
        "type": "object",
        "properties": {
            "task_list": {
                "type": "string",
                "description": "The full content of the updated task list in Markdown format (e.g., - [x] Task 1\n- [ ] Task 2).",
            }
        },
        "required": ["task_list"],
    }

    def __init__(self, orchestrator_ref):
        self.orchestrator = orchestrator_ref

    async def execute(self, **kwargs) -> str:
        # LLM may pass different parameter names, so check multiple possibilities
        task_list = (
            kwargs.get("task_list")
            or kwargs.get("tasks")
            or kwargs.get("content")
            or kwargs.get("list")
            or ""
        )

        if not task_list:
            return "[FAILURE] Missing required parameter: task_list. Please provide task list content."

        self.orchestrator.update_todo_list(task_list)
        return "Task list updated successfully."
