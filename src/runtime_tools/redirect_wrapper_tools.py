"""
重定向包装器工具
为所有工具提供输出重定向到文件和内存的能力
"""

from src.core.capability import BaseTool


class RedirectToFileTool(BaseTool):
    """
    包装器工具：执行指定工具并将输出保存到文件

    使用方式：
        redirect_to_file(tool_name="evaluate_script", tool_params={...}, file="aaa.txt", mode="w")

    特性：
        - 链式调用：先执行工具，再保存输出
        - 执行失败：不保存错误输出
        - 保存失败：返回原工具结果 + 错误信息
        - silent=True：不返回重定向信息
    """

    name = "redirect_to_file"
    description = """Execute any tool and save its output to a file.

This wrapper executes a tool and copies its output to .OneAgent/ directory.
The original tool output is still returned, with an optional note about redirection.

Parameters:
        - tool_name: Name of the tool to execute (e.g., 'evaluate_script', 'bash_command')
        - tool_params: Parameters to pass to the tool (as a dict, default: {})
        - file: Target file path relative to .OneAgent/ (e.g., 'output.txt', 'data/result.json')
        - mode: File mode - 'w' (write, default), 'a' (append), 'a+' (append+read), 'x' (exclusive write)
        - silent: If True, only return the original output without redirection note (default: False)
        - return_original: If True, return the original tool output (default: True). If False, return empty string
    """

    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to execute",
            },
            "tool_params": {
                "type": "object",
                "description": "Parameters to pass to the tool (as a dict)",
                "default": {},
            },
            "file": {
                "type": "string",
                "description": "Target file path relative to .OneAgent/",
            },
            "mode": {
                "type": "string",
                "enum": ["w", "a", "a+", "x"],
                "description": "File mode: w=write, a=append, a+=append+read, x=exclusive write",
                "default": "w",
            },
            "silent": {
                "type": "boolean",
                "description": "If True, only return the original output without redirection note",
                "default": False,
            },
            "return_original": {
                "type": "boolean",
                "description": "If True, return the original tool output. If False, return empty string",
                "default": True,
            },
        },
        "required": ["tool_name", "file"],
    }

    async def execute(self, **kwargs) -> str:
        """Execute tool and redirect output to file"""
        tool_name = kwargs.get("tool_name")
        tool_params = kwargs.get("tool_params", {})
        file_path = kwargs.get("file")
        mode = kwargs.get("mode", "w")
        silent = kwargs.get("silent", False)
        return_original = kwargs.get("return_original", True)

        if not tool_name or not file_path:
            error_msg = "Error: 'tool_name' and 'file' are required parameters"
            if return_original:
                return error_msg
            return ""

        from src.core.registry import global_registry

        tool = global_registry.get_capability(tool_name)

        if not tool:
            error_msg = f"Error: Tool '{tool_name}' not found"
            if return_original:
                return error_msg
            return ""

        result = ""
        try:
            result = await tool.execute(**tool_params)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            if return_original:
                return error_msg
            return ""

        save_error = None
        try:
            from src.runtime_tools.shared_fs_tools import SharedSaveToFileTool

            save_tool = SharedSaveToFileTool()
            await save_tool.execute(filename=file_path, content=result, mode=mode)
        except Exception as e:
            save_error = f"Failed to save output to file: {str(e)}"

        if not return_original:
            return ""

        if save_error:
            if return_original:
                return f"{result}\n\n{save_error}"
            else:
                return f"{save_error}"
        elif silent:
            if return_original:
                return result
            else:
                return ""
        else:
            if return_original:
                return f"{result}\n\n[Output redirected to: .OneAgent/{file_path} (mode: {mode})]"
            else:
                return f"[Output redirected to: .OneAgent/{file_path} (mode: {mode})]"


class RedirectToMemTool(BaseTool):
    """
    包装器工具：执行指定工具并将输出保存到内存

    使用方式：
        redirect_to_mem(tool_name="evaluate_script", tool_params={...})

    特性：
        - 链式调用：先执行工具，再保存输出
        - 执行失败：不保存错误输出
        - 保存失败：返回原工具结果 + 错误信息
        - silent=True：不返回重定向信息
        - return_original=False：返回空字符串
    """

    name = "redirect_to_mem"
    description = """Execute any tool and save its output to shared memory.

This wrapper executes a tool and copies its output to Level 1 shared memory (4K circular buffer).
The original tool output is still returned, with an optional note about copy.

Parameters:
        - tool_name: Name of the tool to execute (e.g., 'evaluate_script', 'bash_command')
        - tool_params: Parameters to pass to the tool (as a dict, default: {})
        - silent: If True, only return the original output without redirection note (default: False)
        - return_original: If True, return the original tool output (default: True). If False, return empty string
    """

    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to execute",
            },
            "tool_params": {
                "type": "object",
                "description": "Parameters to pass to the tool (as a dict)",
                "default": {},
            },
            "silent": {
                "type": "boolean",
                "description": "If True, only return the original output without redirection note",
                "default": False,
            },
            "return_original": {
                "type": "boolean",
                "description": "If True, return the original tool output. If False, return empty string",
                "default": True,
            },
        },
        "required": ["tool_name"],
    }

    async def execute(self, **kwargs) -> str:
        """Execute tool and copy output to memory"""
        tool_name = kwargs.get("tool_name")
        tool_params = kwargs.get("tool_params", {})
        silent = kwargs.get("silent", False)
        return_original = kwargs.get("return_original", True)

        if not tool_name:
            error_msg = "Error: 'tool_name' is a required parameter"
            if return_original:
                return error_msg
            return ""

        from src.core.registry import global_registry

        tool = global_registry.get_capability(tool_name)

        if not tool:
            error_msg = f"Error: Tool '{tool_name}' not found"
            if return_original:
                return error_msg
            return ""

        try:
            result = await tool.execute(**tool_params)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            if return_original:
                return error_msg
            return ""

        save_error = None
        try:
            from src.runtime_tools.memory_io_tools import MemoryWriteTool

            memory_tool = MemoryWriteTool()
            await memory_tool.execute(content=result)
        except Exception as e:
            save_error = f"Failed to save output to memory: {str(e)}"

        if not return_original:
            return ""

        if save_error:
            return f"{result}\n\n{save_error}"
        elif silent:
            return result
        else:
            return f"{result}\n\n[Output copied to shared memory (Level 1: 4K circular buffer)]"


class RedirectToFileAndMemTool(BaseTool):
    """
    组合包装器：同时输出到文件和内存

    使用方式：
        redirect_to_file_and_mem(tool_name="evaluate_script", tool_params={...}, file="aaa.txt")

    特性：
        - 链式调用：先执行工具，再保存到文件和内存
        - 执行失败：不保存错误输出
        - 保存失败：返回原工具结果 + 错误信息
        - silent=True：不返回重定向信息
        - return_original=False：返回空字符串
    """

    name = "redirect_to_file_and_mem"
    description = """Execute any tool and save its output to both file and shared memory.

This wrapper executes a tool and copies its output to both .OneAgent/ directory and Level 1 shared memory.

Parameters:
        - tool_name: Name of the tool to execute (e.g., 'evaluate_script', 'bash_command')
        - tool_params: Parameters to pass to the tool (as a dict, default: {})
        - file: Target file path relative to .OneAgent/
        - mode: File mode (default: 'w')
        - silent: If True, only return the original output without redirection note (default: False)
        - return_original: If True, return the original tool output (default: True). If False, return empty string
    """

    parameters = {
        "type": "object",
        "properties": {
            "tool_name": {
                "type": "string",
                "description": "Name of the tool to execute",
            },
            "tool_params": {
                "type": "object",
                "description": "Parameters to pass to the tool (as a dict)",
                "default": {},
            },
            "file": {
                "type": "string",
                "description": "Target file path relative to .OneAgent/",
            },
            "mode": {
                "type": "string",
                "enum": ["w", "a", "a+", "x"],
                "description": "File mode: w=write, a=append, a+=append+read, x=exclusive write",
                "default": "w",
            },
            "silent": {
                "type": "boolean",
                "description": "If True, only return the original output without redirection note",
                "default": False,
            },
            "return_original": {
                "type": "boolean",
                "description": "If True, return the original tool output. If False, return empty string",
                "default": True,
            },
        },
        "required": ["tool_name", "file"],
    }

    async def execute(self, **kwargs) -> str:
        """Execute tool and redirect output to both file and memory"""
        tool_name = kwargs.get("tool_name")
        tool_params = kwargs.get("tool_params", {})
        file_path = kwargs.get("file")
        mode = kwargs.get("mode", "w")
        silent = kwargs.get("silent", False)
        return_original = kwargs.get("return_original", True)

        if not tool_name or not file_path:
            error_msg = "Error: 'tool_name' and 'file' are required parameters"
            if return_original:
                return error_msg
            return ""

        from src.core.registry import global_registry

        tool = global_registry.get_capability(tool_name)

        if not tool:
            error_msg = f"Error: Tool '{tool_name}' not found"
            if return_original:
                return error_msg
            return ""

        try:
            result = await tool.execute(**tool_params)
        except Exception as e:
            error_msg = f"Tool execution failed: {str(e)}"
            if return_original:
                return error_msg
            return ""

        file_error = None
        mem_error = None

        try:
            from src.runtime_tools.shared_fs_tools import SharedSaveToFileTool

            save_tool = SharedSaveToFileTool()
            await save_tool.execute(filename=file_path, content=result, mode=mode)
        except Exception as e:
            file_error = f"Failed to save output to file: {str(e)}"

        try:
            from src.runtime_tools.memory_io_tools import MemoryWriteTool

            memory_tool = MemoryWriteTool()
            await memory_tool.execute(content=result)
        except Exception as e:
            mem_error = f"Failed to save output to memory: {str(e)}"

        if not return_original:
            return ""

        errors = []
        if file_error:
            errors.append(file_error)
        if mem_error:
            errors.append(mem_error)

        if errors:
            error_msg = "\n\n".join(errors)
            return f"{result}\n\n{error_msg}"
        elif silent:
            return result
        else:
            return f"{result}\n\n[Output redirected to: .OneAgent/{file_path} (mode: {mode}) and shared memory]"
