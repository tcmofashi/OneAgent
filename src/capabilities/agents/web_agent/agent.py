from typing import Optional
from src.core.react_agent import ReactAgent
# Tools will be loaded by the loader from the ./tools directory

class WebAgent(ReactAgent):
    """
    Web Agent capable of browsing the internet using Playwright.
    can navigate, click, type, and read web pages.
    """
    name: str = "web_agent"
    description: str = "A web agent that uses Playwright to browse the internet. Can navigate to URLs, click elements, fill forms, and read page content."
    model_label: Optional[str] = None
    model_role: str = "web_browsing" # Changed from hardcoded Qwen model to configurable role
    
    # Tools are automatically populated by the loader from the tools/ directory
    # But we can also specify default allowed tools if we wanted to restrict it further
    # For now, we rely on the loader adding them to self.allowed_tools
    max_iterations: int = 50  # Increased for complex web tasks; context compression handles overflow
    
    def build_full_prompt(self, instruction: str = "", context: str = "", upstream_capabilities: str = "", language: str = "zh") -> str:
        """
        Inject specific instructions for WebAgent regarding browser state.
        """
        # Get base prompt
        prompt = super().build_full_prompt(instruction, context, upstream_capabilities, language)
        
        # Add WebAgent specific rules
        additional_rules = """
## 网页保持逻辑 (Web Page Persistence Logic)
- 默认情况下，任务结束（SUCCESS/FAILURE）后浏览器状态可能会重置或关闭。
- **如果你希望保持网页/浏览器打开**（例如为了让用户查看结果，或进行后续交互），你必须使用 `report_status(status="INTERRUPTED", message="...")`。
- 在 message 中明确说明维持浏览器打开的原因。
- 如果任务完全完成且不需要用户查看网页，使用 `status="SUCCESS"`。

## Web Page Persistence Logic
- By default, the browser state may be reset or closed after task completion (SUCCESS/FAILURE).
- **If you want to keep the webpage/browser OPEN** (e.g., for user inspection or follow-up), you MUST use `report_status(status="INTERRUPTED", message="...")`.
- Explicitly state the reason for keeping the browser open in the message.
- If the task is fully complete and user inspection is not needed, use `status="SUCCESS"`.
"""
        return prompt + additional_rules
