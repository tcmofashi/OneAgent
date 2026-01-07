from pathlib import Path
import asyncio
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from typing import Optional

from src.core.capability import BaseAgent
from src.core.config import global_config


class QwenBridgeAgent(BaseAgent):
    """
    An adapter agent that delegates tasks to the Qwen Code CLI via a bridge script.
    """
    name: str = "qwen_bridge_agent"
    description: str = "A powerful coding agent backed by Qwen Code CLI."
    
    AGENT_DIR = Path(__file__).resolve().parent
    BRIDGE_SCRIPT_PATH: str = str(AGENT_DIR / "cli_dist" / "dist" / "oneagent-bridge.js")
    
    language: str = "zh"
    NODE_BIN: str = "node"
    allowed_tools: list[str] = ["report_status"]

    # 能力描述 - 简洁格式，与其他能力保持一致
    # 详细说明供 Orchestrator 理解此 Agent 适合处理的任务类型
    CAPABILITIES_SUMMARY = "代码编辑, 命令行执行(bash/git/npm/pip/docker), Web搜索, 文件操作"

    def get_context_description(self) -> str:
        """
        返回简洁的能力描述，与其他 Agent/Tool 格式一致。
        用于 Orchestrator 的能力树展示和任务匹配。
        """
        return f"{self.name} (Agent): 强大的编程代理 [{self.CAPABILITIES_SUMMARY}] [Tools: {', '.join(self.allowed_tools)}]"

    # Debug patterns to filter out
    DEBUG_PATTERNS = [
        r"^\[DEBUG\]",
        r"^\[BfsFileSearch\]",
        r"^\[MemoryDiscovery\]",
        r"^QwenLogger:",
        r"^ToolRegistry created",
        r"^Scanning \[",
        r"^Tool with name .* is already registered",
        r"^consecutive429Count",
        r"^\[bridge\]",
        r"^RUM flush failed",
        r"^Flushing log events",
        r"^Error report available at:",
        # Filter Node.js error stack traces and warnings
        r"^\s*at .+\(node:.+\)",  # Stack trace lines
        r"^\s*code: 'ECONNRESET'",
        r"^\s*host: '.*rum\.aliyuncs\.com'",
        r"^\s*port: 443",
        r"^\s*localAddress:",
        r"^\s*path: null",
        r"^Client network socket disconnected",
        r"^\s*\}", # Closing brace of error object
    ]
    
    def _should_filter_line(self, line: str) -> bool:
        """Check if a line should be filtered (debug message)."""
        for pattern in self.DEBUG_PATTERNS:
            if re.search(pattern, line.strip()):
                return True
        return False

    def _get_node_binary(self) -> str:
        """Resolve Node.js binary path, checking system PATH and common locations."""
        # 1. Check system PATH
        if shutil.which("node"):
            return "node"
        
        # 2. Check common Windows locations
        if os.name == 'nt':
            common_paths = [
                r"C:\Program Files\nodejs\node.exe",
                r"C:\Program Files (x86)\nodejs\node.exe",
                os.path.expandvars(r"%ProgramFiles%\nodejs\node.exe")
            ]
            for path in common_paths:
                if os.path.exists(path):
                    return path
        
        return "node"

    async def _create_subprocess_compat(self, cmd: list, cwd: str, env: dict):
        """
        Create a subprocess compatible with Windows async limitations.
        Falls back to subprocess.Popen with thread-based stream reading when
        asyncio.create_subprocess_exec raises NotImplementedError on Windows.
        """
        try:
            # Try the native asyncio subprocess first
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            return process, False  # False = using native asyncio
        except NotImplementedError:
            # Windows fallback: use subprocess.Popen with threading
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env
            )
            return process, True  # True = using Popen fallback

    async def _read_popen_stream_async(self, stream, buffer: list, callback, is_stderr: bool = False):
        """
        Read from a Popen stream in a thread-safe async manner with REAL-TIME output.
        Uses a queue to pass lines from the reader thread to the async consumer.
        """
        line_queue = queue.Queue()
        
        def reader_thread():
            """Blocking reader thread that puts lines in the queue."""
            try:
                for line in iter(stream.readline, b''):
                    if not line:
                        break
                    decoded = line.decode('utf-8')
                    line_queue.put(decoded)
            except Exception:
                pass
            finally:
                line_queue.put(None)  # Sentinel to signal end
                try:
                    stream.close()
                except Exception:
                    pass
        
        # Start reader thread
        reader = threading.Thread(target=reader_thread, daemon=True)
        reader.start()
        
        loop = asyncio.get_event_loop()
        
        # Consume lines from queue in async manner
        while True:
            try:
                # Non-blocking get with small timeout, then yield to event loop
                line = await loop.run_in_executor(None, lambda: line_queue.get(timeout=0.1))
                if line is None:  # End sentinel
                    break
                buffer.append(line)
                callback(line, is_stderr)
            except queue.Empty:
                # No data yet, yield to event loop
                await asyncio.sleep(0.01)
            except Exception as e:
                # Only break on real errors, not queue.Empty
                if not isinstance(e, queue.Empty):
                    break
        
        reader.join(timeout=1.0)

    def _format_stream_json(self, json_str: str) -> Optional[str]:
        """Parse and format a single stream-json line for beautiful display."""
        try:
            msg = json.loads(json_str)
            msg_type = msg.get("type", "")
            
            # System init message
            if msg_type == "system" and msg.get("subtype") == "init":
                tools = msg.get("tools", [])
                return f"  📦 CLI 初始化完成 | 可用工具: {len(tools)} 个"
            
            # Assistant message
            elif msg_type == "assistant":
                content = msg.get("message", {}).get("content", [])
                lines = []
                for item in content:
                    if item.get("type") == "thinking":
                        thinking = item.get("thinking", "")
                        if thinking:
                            if len(thinking) > 500:
                                thinking = thinking[:500] + "..."
                            lines.append(f"  💭 思考: {thinking}")
                    
                    elif item.get("type") == "text":
                        text = item.get("text", "").strip()
                        if text:
                            lines.append(f"  💬 输出: {text}")
                    
                    elif item.get("type") == "tool_use":
                        tool_name = item.get("name", "unknown")
                        tool_input = item.get("input", {})
                        
                        if tool_name == "report_status":
                            status = tool_input.get("status", "unknown")
                            message = tool_input.get("message") or tool_input.get("result") or tool_input.get("summary", "")
                            emoji = {"success": "✅", "failure": "❌", "rejected": "🚫", "interrupted": "⏸️"}.get(status, "❓")
                            lines.append(f"  {emoji} 状态报告: [{status.upper()}] {message}")
                        else:
                            input_preview = json.dumps(tool_input, ensure_ascii=False)[:100]
                            if len(json.dumps(tool_input, ensure_ascii=False)) > 100:
                                input_preview += "..."
                            lines.append(f"  🔧 调用工具: {tool_name}({input_preview})")
                
                return "\n".join(lines) if lines else None
            
            # Tool result (user message with tool_result)
            elif msg_type == "user":
                content = msg.get("message", {}).get("content", [])
                for item in content:
                    if item.get("type") == "tool_result":
                        result_content = item.get("content", "")
                        if result_content:
                            if len(result_content) > 200:
                                result_content = result_content[:200] + "..."
                            return f"  📋 工具结果: {result_content}"
            
            # Final result
            elif msg_type == "result":
                duration = msg.get("duration_ms", 0)
                turns = msg.get("num_turns", 0)
                return f"  🏁 完成 | 耗时: {duration/1000:.1f}s | 轮次: {turns}"
            
            return None
            
        except json.JSONDecodeError:
            return None

    def _format_output_line(self, line: str, is_stderr: bool = False) -> Optional[str]:
        """Format a line for display, returning None if should be hidden."""
        stripped = line.strip()
        if not stripped:
            return None
            
        if self._should_filter_line(stripped):
            return None
        
        # Try to parse as stream-json (single JSON object per line)
        if stripped.startswith("{"):
            return self._format_stream_json(stripped)
        
        # Format stderr errors
        if is_stderr and not self._should_filter_line(stripped):
            return f"  ⚠️  {stripped}"
        
        return None

    async def execute(self, instruction: str, context: Optional[str] = None, upstream_capabilities: Optional[str] = None) -> str:
        """
        Executes the instruction by invoking the Qwen Code CLI bridge.
        """
        # 1. Build the full prompt
        full_prompt = self.build_full_prompt(
            instruction=instruction,
            context=context,
            upstream_capabilities=upstream_capabilities,
            language=self.language
        )
        
        # 2. Prepare the command
        if not os.path.exists(self.BRIDGE_SCRIPT_PATH):
            return f"FAILURE: Bridge script not found at {self.BRIDGE_SCRIPT_PATH}"

        node_bin = self._get_node_binary()
        cmd = [node_bin, self.BRIDGE_SCRIPT_PATH, full_prompt]
        
        # Print header and FULL PROMPT
        print(f"\n{'='*60}")
        print(f"🚀 [QwenCLI] 启动子代理")
        print(f"{'='*60}")
        print(f"\n📄 【完整 Prompt】:")
        print(f"{'─'*40}")
        # Print prompt with proper indentation
        for line in full_prompt.split('\n'):
            print(f"  {line}")
        print(f"{'─'*40}")
        print(f"  共 {len(full_prompt)} 字符\n")
        
        # Prepare environment
        env = os.environ.copy()
        
        target_model_label = global_config.get("llm.functional_roles.code_generation")
        if not target_model_label:
            target_model_label = global_config.get("llm.active_model_label")
        
        try:
            api_base, api_key, model_name = global_config.get_model_config(target_model_label)
            
            env["OPENAI_API_KEY"] = api_key
            env["OPENAI_BASE_URL"] = api_base
            
            # CRITICAL: Disable telemetry at process level to prevent network errors
            env["QWEN_DISABLE_TELEMETRY"] = "true"
            env["QWEN_CODE_TELEMETRY_DISABLED"] = "1"
            
            print(f"  🤖 模型: {model_name}")
            print(f"{'='*60}\n")
            
            cmd.extend(["--model", model_name])
            cmd.extend(["--auth-type", "openai"]) 
            cmd.extend(["--openai-base-url", api_base])
            
        except Exception as e:
            return f"FAILURE: Could not load configuration for '{target_model_label}': {e}"

        try:
            process, is_popen_fallback = await self._create_subprocess_compat(
                cmd, os.getcwd(), env
            )

            stdout_buffer = []
            stderr_buffer = []
            
            # Track the last report_status tool call for accurate status reporting
            # Structure matches OneAgent standard: status, message
            last_report_status = {
                "status": None, 
                "message": None
            }

            def process_line(decoded_line: str, is_stderr: bool = False):
                """Process a line of output (used by both async modes)."""
                nonlocal last_report_status
                
                # Try to capture report_status tool calls from stream-json
                stripped = decoded_line.strip()
                if stripped.startswith("{"):
                    try:
                        msg = json.loads(stripped)
                        if msg.get("type") == "assistant":
                            content = msg.get("message", {}).get("content", [])
                            for item in content:
                                if item.get("type") == "tool_use" and item.get("name") == "report_status":
                                    tool_input = item.get("input", {})
                                    # Normalize status to lowercase
                                    status = tool_input.get("status", "").lower()
                                    # Support message, fallback to result/summary/reason/mismatch for compatibility
                                    message = tool_input.get("message") or \
                                              tool_input.get("result") or \
                                              tool_input.get("summary") or \
                                              tool_input.get("reason") or \
                                              tool_input.get("mismatch_detail") or ""
                                    
                                    if status and message:
                                        last_report_status = {
                                            "status": status, 
                                            "message": message
                                        }
                    except json.JSONDecodeError:
                        pass
                
                # Format and display immediately (streaming)
                formatted = self._format_output_line(decoded_line, is_stderr)
                if formatted:
                    print(formatted, flush=True)
                    sys.stdout.flush()

            if is_popen_fallback:
                # Windows Popen fallback: use thread-based async reading
                await asyncio.gather(
                    self._read_popen_stream_async(process.stdout, stdout_buffer, process_line, False),
                    self._read_popen_stream_async(process.stderr, stderr_buffer, process_line, True)
                )
                # Wait for process to complete
                loop = asyncio.get_event_loop()
                returncode = await loop.run_in_executor(None, process.wait)
            else:
                # Native asyncio subprocess: stream output with real-time formatting
                async def read_stream(stream, buffer, is_stderr=False):
                    while True:
                        line = await stream.readline()
                        if not line:
                            break
                        decoded_line = line.decode('utf-8')
                        buffer.append(decoded_line)
                        process_line(decoded_line, is_stderr)

                await asyncio.gather(
                    read_stream(process.stdout, stdout_buffer),
                    read_stream(process.stderr, stderr_buffer, is_stderr=True)
                )
                await process.wait()
                returncode = process.returncode

            if returncode != 0:
                error_msg = "".join(stderr_buffer)
                print(f"\n  ❌ CLI 退出码: {returncode}")
                return f"FAILURE: Qwen CLI exited with code {returncode}. Stderr: {error_msg}"

            # Use captured report_status if available
            if last_report_status["status"] and last_report_status["message"]:
                status = last_report_status["status"]
                message = last_report_status["message"]
                return f"Task Completed.\nStatus: {status}\nResult: {message}"
            else:
                # Fall back: Parse __ONEAGENT_RESULT__ marker
                marker = "__ONEAGENT_RESULT__:"
                result_line = None
                
                for line in reversed(stdout_buffer):
                    if marker in line:
                        result_line = line.strip()
                        break
                
                if not result_line:
                    return "FAILURE: Qwen CLI finished but did not return a structured result."
                
                json_str = result_line.split(marker, 1)[1]
                try:
                    result_json = json.loads(json_str)
                    status = result_json.get("status", "success")
                    # Support both result and summary in fallback
                    summary = result_json.get("result") or result_json.get("summary", "No result provided.")
                except json.JSONDecodeError:
                    return f"FAILURE: Failed to parse bridge result JSON: {json_str}"
            
            print(f"\n{'='*60}")
            emoji = {"success": "✅", "failure": "❌", "rejected": "🚫", "interrupted": "⏸️"}.get(status, "❓")
            print(f"{emoji} [QwenCLI] 任务完成 | 状态: {status.upper()}")
            print(f"{'='*60}\n")
            
            return f"Task Completed.\nStatus: {status}\nResult: {summary}"

        except Exception as e:
            import traceback
            traceback.print_exc()
            return f"FAILURE: Exception running Qwen CLI bridge: {str(e)}"
