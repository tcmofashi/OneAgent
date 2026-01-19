import asyncio
import atexit
import signal
from typing import Optional, Dict, Any, List
from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page,
    ElementHandle,
)

from src.core.capability import BaseTool


class PlaywrightManager:
    """
    Singleton manager for Playwright browser instance.
    Keeps browser open across multiple tool calls in the same session.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlaywrightManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._initialized = True
        self._cleanup_registered = False

    async def get_page(self) -> Page:
        """
        Get the current active page. Initializes browser if needed.
        """
        if not self._playwright:
            self._playwright = await async_playwright().start()

        if not self._browser:
            # Launch headless by default, can be configured
            self._browser = await self._playwright.chromium.launch(headless=False)

        if not self._context:
            self._context = await self._browser.new_context()

        if not self._page:
            self._page = await self._context.new_page()

        # Register cleanup on first use
        if not self._cleanup_registered:
            self._register_cleanup()
            self._cleanup_registered = True

        return self._page

    def _register_cleanup(self):
        """Register cleanup handlers for graceful shutdown."""
        atexit.register(self._sync_cleanup)

    def _sync_cleanup(self):
        """
        Synchronous cleanup called by atexit.
        """
        try:
            # Check if we're in a normal exit (not atexit cleanup)
            # Use try-except to detect Python shutdown
            try:
                # This will fail if Python is shutting down
                1 / 0
            except (ZeroDivisionError, TypeError):
                # Python is in shutdown, skip cleanup
                return

            # Try to get running loop, if none exists create one for cleanup
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            if loop.is_running():
                # Schedule cleanup in running loop
                loop.create_task(self.close())
            else:
                # Run cleanup synchronously
                loop.run_until_complete(self.close())
        except Exception:
            # Silently ignore cleanup errors on exit
            pass

    async def close(self):
        """
        Cleanup resources.
        """
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None

        self._page = None


# Global instance
playwright_manager = PlaywrightManager()


class NavigateTool(BaseTool):
    name: str = "navigate"
    description: str = "Navigate to a specific URL in the browser."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "url": {
                "type": "string",
                "description": "The URL to navigate to (must include http/https).",
            }
        },
        "required": ["url"],
    }

    async def execute(self, url: str) -> str:
        try:
            page = await playwright_manager.get_page()
            await page.goto(url)
            title = await page.title()
            return f"Successfully navigated to {url}. Page title: {title}"
        except Exception as e:
            return f"Error navigating to {url}: {str(e)}"


class ClickTool(BaseTool):
    name: str = "click"
    description: str = "Click an element on the current page using a selector."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector or text selector for the element to click.",
            }
        },
        "required": ["selector"],
    }

    async def execute(self, selector: str) -> str:
        try:
            page = await playwright_manager.get_page()

            # 0. 检查匹配元素数量
            locator = page.locator(selector)
            count = await locator.count()

            if count == 0:
                return f"没有找到匹配的元素: {selector}"

            if count > 1:
                # 多个匹配：收集元素信息帮助模型精确化
                details = []
                for i in range(min(count, 5)):  # 最多显示前5个
                    el = locator.nth(i)
                    try:
                        tag = await el.evaluate("el => el.tagName.toLowerCase()")
                        text = await el.evaluate(
                            "el => el.innerText?.substring(0, 50) || ''"
                        )
                        href = await el.evaluate("el => el.getAttribute('href') || ''")
                        classes = await el.evaluate("el => el.className || ''")
                        info = f'  [{i + 1}] <{tag}> text="{text.strip()}" href="{href}" class="{classes}"'
                        details.append(info)
                    except:
                        details.append(f"  [{i + 1}] (无法获取详情)")

                details_str = "\n".join(details)
                return f"选择器 '{selector}' 匹配了 {count} 个元素。请提供更精确的选择器：\n{details_str}"

            # count == 1: 唯一匹配，执行点击
            # Attempt 1: Standard smart click (waits for actionable)
            try:
                await page.click(selector, timeout=2000)
                return f"Successfully clicked element: {selector}"
            except Exception:
                pass

            # Attempt 2: JS Scroll to center + Click
            print(f"Standard click failed for {selector}, attempting JS scroll...")
            try:
                # Locate element handle to ensure it exists before scrolling
                handle = await page.wait_for_selector(
                    selector, state="attached", timeout=2000
                )
                if handle:
                    await handle.evaluate(
                        "el => el.scrollIntoView({block: 'center', inline: 'center'})"
                    )
                    await page.click(selector, timeout=2000)
                    return f"Successfully clicked element (after scroll): {selector}"
            except Exception:
                pass

            # Attempt 3: Force Click (bypasses checks)
            print(f"Scroll click failed for {selector}, attempting force click...")
            await page.click(selector, force=True)
            return f"Successfully force-clicked element: {selector}"

        except Exception as e:
            return f"Error clicking element {selector}: {str(e)}"


class FillTool(BaseTool):
    name: str = "fill"
    description: str = "Fill a text input field on the current page."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "selector": {
                "type": "string",
                "description": "CSS selector for the input element.",
            },
            "text": {
                "type": "string",
                "description": "The text to fill into the field.",
            },
        },
        "required": ["selector", "text"],
    }

    async def execute(self, selector: str, text: str) -> str:
        try:
            page = await playwright_manager.get_page()
            await page.fill(selector, text)
            return f"Successfully filled {selector} with text."
        except Exception as e:
            return f"Error filling element {selector}: {str(e)}"


class GetPageInfoTool(BaseTool):
    name: str = "get_page_info"
    description: str = "Get the current page title, URL, and content dump (text)."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "include_html": {
                "type": "boolean",
                "description": "Whether to return the full HTML content (caution: large). Default False.",
            }
        },
    }

    async def execute(self, include_html: bool = False) -> str:
        try:
            page = await playwright_manager.get_page()
            title = await page.title()
            url = page.url

            if include_html:
                content = await page.content()
            else:
                # Get plain text content
                content = await page.evaluate("document.body.innerText")

            return f"URL: {url}\nTitle: {title}\n\nContent:\n{content[:25000]}..."  # Truncate for safety
        except Exception as e:
            return f"Error getting page info: {str(e)} Type: {type(page)}"


class EvaluateScriptTool(BaseTool):
    name: str = "evaluate_script"
    description: str = """Evaluate JavaScript on the current page.

NOTE: Script is executed as an EXPRESSION, not a function body.
- ❌ DO NOT use 'return': return [1,2,3] will cause SyntaxError
- ✅ Just write expression: [1,2,3] or document.body.innerText
- ✅ For complex logic use IIFE: (() => { const x = []; /*...*/ return x })()

PIPE FEATURE: Use save_to_file parameter to directly save result to tmp/ directory."""
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "script": {
                "type": "string",
                "description": "JavaScript expression to evaluate. Do NOT use 'return' unless inside an IIFE.",
            },
            "save_to_file": {
                "type": "string",
                "description": "Optional: Save result to this file in tmp/ directory (e.g., 'result.txt', 'data.json'). If not provided, result is only returned.",
            },
        },
        "required": ["script"],
    }

    async def execute(self, script: str, save_to_file: Optional[str] = None) -> str:
        try:
            page = await playwright_manager.get_page()
            result = await page.evaluate(script)

            # Convert result to string for saving
            if isinstance(result, (dict, list)):
                import json

                result_str = json.dumps(result, ensure_ascii=False, indent=2)
            else:
                result_str = str(result)

            # Pipe to file if requested
            if save_to_file:
                from .file_tools import _validate_path, _ensure_tmp_dir

                is_valid, full_path, error = _validate_path(save_to_file)
                if not is_valid:
                    return f"Script executed but file save failed: {error}\n\nResult: {result_str}"

                # Ensure parent directories exist
                full_path.parent.mkdir(parents=True, exist_ok=True)

                with open(full_path, "w", encoding="utf-8") as f:
                    f.write(result_str)

                return f"Script executed and result saved to .OneAgent/{save_to_file} ({len(result_str)} chars)\n\nResult preview: {result_str[:500]}{'...' if len(result_str) > 500 else ''}"

            return f"Script execution result: {result}"
        except Exception as e:
            return f"Error executing script: {str(e)}"


class PressTool(BaseTool):
    name: str = "press"
    description: str = "Press a specific key on the keyboard."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "key": {
                "type": "string",
                "description": "The key to press (e.g., 'Enter', 'Tab', 'Escape').",
            }
        },
        "required": ["key"],
    }

    async def execute(self, key: str) -> str:
        try:
            page = await playwright_manager.get_page()
            await page.keyboard.press(key)
            return f"Successfully pressed key: {key}"
        except Exception as e:
            return f"Error pressing key {key}: {str(e)}"


class ScreenshotTool(BaseTool):
    name: str = "screenshot"
    description: str = "Capture a screenshot of the current page for debugging."
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Name for the screenshot file (without extension).",
            }
        },
        "required": ["name"],
    }

    async def execute(self, name: str) -> str:
        try:
            page = await playwright_manager.get_page()
            # Ensure tmp directory exists
            import os

            os.makedirs("tmp_screenshot", exist_ok=True)
            path = f"tmp_screenshot/{name}.png"
            await page.screenshot(path=path)
            return f"Screenshot saved to {path}"
        except Exception as e:
            return f"Error taking screenshot: {str(e)}"


class GetCleanContentTool(BaseTool):
    """
    Extract clean text content from the current page using trafilatura.
    Removes CSS, JavaScript, ads, and other noise - returns only the main text content.
    """

    name: str = "get_clean_content"
    description: str = """Extract clean text content from the current page.

Uses trafilatura to intelligently extract the main content, removing:
- CSS stylesheets and JavaScript
- Navigation menus, headers, footers
- Ads and sidebars
- HTML tags and formatting

Returns clean, readable text - ideal for analyzing page content.
Use this instead of get_page_info when you only need the text content."""
    parameters: Dict[str, Any] = {
        "type": "object",
        "properties": {
            "include_links": {
                "type": "boolean",
                "description": "Whether to include hyperlinks in the output. Default: False",
                "default": False,
            },
            "include_tables": {
                "type": "boolean",
                "description": "Whether to include table content. Default: True",
                "default": True,
            },
        },
    }

    async def execute(
        self, include_links: bool = False, include_tables: bool = True
    ) -> str:
        try:
            import trafilatura

            page = await playwright_manager.get_page()
            url = page.url

            # Get the full HTML content
            html_content = await page.content()

            # Extract clean content using trafilatura
            clean_text = trafilatura.extract(
                html_content,
                include_links=include_links,
                include_tables=include_tables,
                include_comments=False,
                include_formatting=False,
                favor_recall=True,  # Get more content rather than less
            )

            if clean_text:
                # Truncate if too long
                if len(clean_text) > 10000:
                    clean_text = (
                        clean_text[:10000]
                        + "\n\n... [Content truncated, 10000 chars shown]"
                    )
                return f"URL: {url}\n\nClean Content:\n{clean_text}"
            else:
                # Fallback to basic text extraction
                text = await page.evaluate("document.body.innerText")
                if len(text) > 5000:
                    text = text[:5000] + "\n... [Truncated]"
                return f"URL: {url}\n\n[Trafilatura extraction returned empty, using fallback]\n{text}"

        except ImportError:
            return (
                "Error: trafilatura library not installed. Run: pip install trafilatura"
            )
        except Exception as e:
            return f"Error extracting clean content: {str(e)}"
