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
    result: Any # The actual output or error message
    reason: Optional[str] = None # For failure/rejection
    mismatch_detail: Optional[str] = None # Specifically for REJECTED
