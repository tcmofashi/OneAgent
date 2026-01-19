from src.core.capability import BaseTool


class ReportStatusTool(BaseTool):
    name = "report_status"
    description = "Report the final status of your task execution. Use this to finish your work. All details, results, reasoning, or error messages must be included in the 'message' field."
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["SUCCESS", "FAILURE", "REJECTED", "INTERRUPTED"],
                "description": "The outcome of the task. SUCCESS for completion, FAILURE for errors, REJECTED for out of scope, INTERRUPTED for needing help.",
            },
            "message": {
                "type": "string",
                "description": "The detailed content of the report. This includes the task result, error details, refusal reasons, or request for help.",
            },
        },
        "required": ["status", "message"],
    }

    async def execute(self, **kwargs) -> str:
        """
        Execute the status report.
        Supports flexible parameter names to handle LLM variations.
        """
        # 灵活参数处理：接受多种可能的参数名
        status = (
            kwargs.get("status")
            or kwargs.get("state")
            or kwargs.get("result")
            or "SUCCESS"  # 默认值
        )

        message = (
            kwargs.get("message")
            or kwargs.get("msg")
            or kwargs.get("content")
            or kwargs.get("summary")
            or kwargs.get("detail")
            or kwargs.get("reason")
            or "(No message provided)"
        )

        # 标准化 status
        status = status.upper() if isinstance(status, str) else "SUCCESS"
        if status not in ["SUCCESS", "FAILURE", "REJECTED", "INTERRUPTED"]:
            status = "SUCCESS"

        return f"[{status}] {message}"
