from typing import Optional, List
from src.core.react_agent import ReactAgent
from src.core.capability import AgentPromptContext
# Tools will be loaded by the loader from the ./tools directory


class WebAgent(ReactAgent):
    """
    Web Agent capable of browsing the internet using Playwright.
    can navigate, click, type, and read web pages.
    """

    name: str = "web_agent"
    description: str = "A web agent that uses Playwright to browse the internet. Can navigate to URLs, click elements, fill forms, and read page content."
    model_label: Optional[str] = None
    model_role: str = (
        "web_browsing"  # Changed from hardcoded Qwen model to configurable role
    )

    # 能力描述 - 简洁格式
    CAPABILITIES_SUMMARY = (
        "网页导航, 元素点击, 表单填写, 内容读取, 截图, JS执行, 文件操作(.OneAgent目录)"
    )

    def get_context_description(self) -> str:
        """返回简洁的能力描述"""
        return f"{self.name} (Agent): 网页浏览代理 [{self.CAPABILITIES_SUMMARY}] [Tools: {', '.join(self.allowed_tools)}]"

    # Tools are automatically populated by the loader from the tools/ directory
    # But we can also specify default allowed tools if we wanted to restrict it further
    # For now, we rely on the loader adding them to self.allowed_tools
    max_iterations: int = (
        50  # Increased for complex web tasks; context compression handles overflow
    )

    def get_custom_sections(self, ctx: "AgentPromptContext") -> List[str]:
        """
        WebAgent 自定义段落。

        追加 WebAgent 特定规则：
        - 文件操作权限
        - 网页保持逻辑
        """
        sections = []

        if ctx.language == "zh":
            sections.append(f"## 文件操作权限")
        else:
            sections.append("## File Operation Permissions")
        sections.append(
            f"- 你可以使用 `save_to_file`, `read_file`, `list_files`, `delete_file` 工具操作文件"
        )
        sections.append(
            f"- **重要**: 所有文件操作**仅限于 `.OneAgent/` 目录**，你在其他目录没有读写权限"
        )
        sections.append(f"- 默认保存目录: `.OneAgent/`")
        sections.append(f"- 如需保存 evaluate_script 的结果，使用 `save_to_file` 工具")
        sections.append(
            f'- 文件路径使用相对路径，如 "result.txt" 或 "data/output.json"'
        )
        sections.append("")

        if ctx.language == "zh":
            sections.append(f"## 网页保持逻辑")
        else:
            sections.append("## Web Page Persistence Logic")
        sections.append(
            f"- 默认情况下，任务结束（SUCCESS/FAILURE）后浏览器状态可能会重置或关闭。"
        )
        sections.append(
            f'- **如果你希望保持网页/浏览器打开**（例如为了让用户查看结果，或进行后续交互），你必须使用 `report_status(status="INTERRUPTED", message="...")`。'
        )
        sections.append(f"- 在 message 中明确说明维持浏览器打开的原因。")
        sections.append(
            f'- 如果任务完全完成且不需要用户查看网页，使用 `status="SUCCESS"`。'
        )

        return sections
