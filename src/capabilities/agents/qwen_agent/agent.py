from pathlib import Path
import asyncio
import json
import os
import re
import sys
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
    ]
    
    def _should_filter_line(self, line: str) -> bool:
        """Check if a line should be filtered (debug message)."""
        for pattern in self.DEBUG_PATTERNS:
            if re.search(pattern, line.strip()):
                return True
        return False
    
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
                            summary = tool_input.get("summary", "")
                            emoji = {"success": "✅", "failure": "❌", "rejected": "🚫", "interrupted": "⏸️"}.get(status, "❓")
                            lines.append(f"  {emoji} 状态报告: [{status.upper()}] {summary}")
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

        cmd = [self.NODE_BIN, self.BRIDGE_SCRIPT_PATH, full_prompt]
        
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
            
            print(f"  🤖 模型: {model_name}")
            print(f"{'='*60}\n")
            
            cmd.extend(["--model", model_name])
            cmd.extend(["--auth-type", "openai"]) 
            cmd.extend(["--openai-base-url", api_base])
            
        except Exception as e:
            return f"FAILURE: Could not load configuration for '{target_model_label}': {e}"

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=os.getcwd(), 
                env=env
            )

            stdout_buffer = []
            stderr_buffer = []

            # Stream output with real-time formatting
            async def read_stream(stream, buffer, is_stderr=False):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8')
                    buffer.append(decoded_line)
                    
                    # Format and display immediately (streaming)
                    formatted = self._format_output_line(decoded_line, is_stderr)
                    if formatted:
                        print(formatted, flush=True)
                        sys.stdout.flush()

            await asyncio.gather(
                read_stream(process.stdout, stdout_buffer),
                read_stream(process.stderr, stderr_buffer, is_stderr=True)
            )
            
            await process.wait()

            if process.returncode != 0:
                error_msg = "".join(stderr_buffer)
                print(f"\n  ❌ CLI 退出码: {process.returncode}")
                return f"FAILURE: Qwen CLI exited with code {process.returncode}. Stderr: {error_msg}"

            # Parse Result
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
                result = json.loads(json_str)
                status = result.get("status", "success")
                summary = result.get("summary", "No summary provided.")
                
                print(f"\n{'='*60}")
                emoji = {"success": "✅", "failure": "❌", "rejected": "🚫", "interrupted": "⏸️"}.get(status, "❓")
                print(f"{emoji} [QwenCLI] 任务完成 | 状态: {status.upper()}")
                print(f"{'='*60}\n")
                
                return f"Task Completed.\nStatus: {status}\nSummary: {summary}"
                
            except json.JSONDecodeError:
                return f"FAILURE: Failed to parse bridge result JSON: {json_str}"

        except Exception as e:
            return f"FAILURE: Exception running Qwen CLI bridge: {str(e)}"
