from enum import Enum
from typing import Optional, Any
from pydantic import BaseModel

class AgentStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE" 
    REJECTED = "REJECTED"
    INTERRUPTED = "INTERRUPTED"

class ExecutionResult(BaseModel):
    status: AgentStatus
    result: Any # 实际输出或错误消息 / The actual output or error message
    reason: Optional[str] = None # 失败/拒绝的原因 / For failure/rejection
    mismatch_detail: Optional[str] = None # 专门针对 REJECTED 的详情 / Specifically for REJECTED
