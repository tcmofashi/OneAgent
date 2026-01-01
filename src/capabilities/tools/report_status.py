from src.core.capability import BaseTool
from src.core.protocol import AgentStatus
from typing import Dict, Any

class ReportStatusTool(BaseTool):
    name = "report_status"
    description = "Report the final status of your task execution. Use this to finish your work, report errors, or REJECT tasks that are out of your scope."
    parameters = {
        "type": "object",
        "properties": {
            "status": {
                "type": "string",
                "enum": ["SUCCESS", "FAILURE", "REJECTED", "INTERRUPTED"],
                "description": "The outcome of the task. Use INTERRUPTED to ask for help/upstream tools."
            },
            "result": {
                "type": "string",
                "description": "The result of the execution (if SUCCESS) or error message (if FAILURE)."
            },
            "reason": {
                "type": "string",
                "description": "Detailed reason for FAILURE or REJECTED."
            },
            "mismatch_detail": {
                "type": "string",
                "description": "If status is REJECTED, explain WHY this task is out of your scope."
            }
        },
        "required": ["status", "result"]
    }

    async def execute(self, status: str, result: str, reason: str = "", mismatch_detail: str = "") -> str:
        # 这个实现有点棘手。
        # This implementation is a bit tricky. 
        # 在真实的 Agent 循环中，调用此工具应发出该 Agent 运行结束的信号。
        # In a real Agent loop, calling this tool should signaling the END of that Agent's run.
        # 目前，我们返回一个可供 Orchestrator（或父 Agent）解析的结构化字符串。
        # For now, we return a structured string that the Orchestrator (or parent Agent) can parse.
        
        output = f"[{status}] {result}"
        if reason:
            output += f"\nReason: {reason}"
        if mismatch_detail:
            output += f"\nMismatch: {mismatch_detail}"
            
        # 我们可能希望引发特殊异常或返回特殊对象
        # We might want to raise a special exception or return a special object
        # 以停止循环，但为了工具兼容性，我们返回字符串。
        # to stop the loop, but for tool compatibility we return string.
        return output
