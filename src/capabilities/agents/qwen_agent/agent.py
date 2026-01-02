from pathlib import Path
import asyncio
import json
import os
import subprocess
import shlex
from typing import Optional, Dict, Any

from src.core.capability import BaseAgent
from src.core.registry import global_registry
from src.core.config import global_config

class QwenBridgeAgent(BaseAgent):
    """
    An adapter agent that delegates tasks to the Qwen Code CLI via a bridge script.
    """
    name: str = "qwen_bridge_agent"
    description: str = "A powerful coding agent backed by Qwen Code CLI."
    
    # Path to the CLI bridge script (Relative to Agent Directory)
    # The binaries and dependencies are vendored in ./cli_dist
    AGENT_DIR = Path(__file__).resolve().parent
    BRIDGE_SCRIPT_PATH: str = str(AGENT_DIR / "cli_dist" / "dist" / "oneagent-bridge.js")
    
    # Language for prompt template
    language: str = "zh"

    # We might need to specify the node executable if not in path, but usually 'node' works.
    NODE_BIN: str = "node"
        
    # We allow report_status so the prompt template includes it.
    # The bridge script actually injects the tool, but we list it here for the prompt.
    allowed_tools: list[str] = ["report_status"]

    async def execute(self, instruction: str, context: Optional[str] = None, upstream_capabilities: Optional[str] = None) -> str:
        """
        Executes the instruction by invoking the Qwen Code CLI bridge.
        """
        # 1. Build the full prompt (instruction + context + capabilities)
        full_prompt = self.build_full_prompt(
            context=context,
            upstream_capabilities=upstream_capabilities,
            language=self.language
        )
        
        # 2. Prepare the command
        # We pass the full prompt as the first argument.
        # Ensure we quote it properly for the shell.
        if not os.path.exists(self.BRIDGE_SCRIPT_PATH):
            return f"FAILURE: Bridge script not found at {self.BRIDGE_SCRIPT_PATH}"

        # Usage: node <script> "<prompt>"
        # We utilize subprocess.create_subprocess_exec to handle arguments safely without manual escaping issues
        cmd = [self.NODE_BIN, self.BRIDGE_SCRIPT_PATH, full_prompt]
        
        print(f"[QwenBridgeAgent] Starting CLI bridge with prompt length: {len(full_prompt)}")
        
        # Prepare environment with API keys
        env = os.environ.copy()
        
        # Load Configuration for Qwen Bridge
        # We try to get the specialized 'code_generation' role first, then fallback to active model.
        target_model_label = global_config.get("llm.functional_roles.code_generation")
        if not target_model_label:
             target_model_label = global_config.get("llm.active_model_label")
             print(f"[QwenBridgeAgent] No 'code_generation' role found, falling back to active label: {target_model_label}")
        
        try:
             api_base, api_key, model_name = global_config.get_model_config(target_model_label)
             
             # Inject OpenAI-compatible environment variables
             env["OPENAI_API_KEY"] = api_key
             env["OPENAI_BASE_URL"] = api_base
             
             print(f"[QwenBridgeAgent] Configured for model: {model_name} (Label: {target_model_label})")
             
             # Append arguments to force the CLI to use this model
             cmd.extend(["--model", model_name])
             cmd.extend(["--auth-type", "openai"]) 
             cmd.extend(["--openai-base-url", api_base])
             
        except Exception as e:
             return f"FAILURE: Could not load configuration for '{target_model_label}': {e}"

        try:
            # 3. Run subprocess
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                # cwd needs to be the project root or where the CLI expects to run.
                cwd=os.getcwd(), 
                env=env # Pass current env (including API keys)
            )

            stdout_buffer = []
            stderr_buffer = []

            # 4. Stream output
            # We want to show real-time output (if any) and capture the final result.
            async def read_stream(stream, buffer, is_stderr=False):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    decoded_line = line.decode('utf-8')
                    buffer.append(decoded_line)
                    if is_stderr:
                         print(f"[QwenCLI Stderr] {decoded_line}", end="")
                    else:
                         print(f"[QwenCLI Stdout] {decoded_line}", end="")

            await asyncio.gather(
                read_stream(process.stdout, stdout_buffer),
                read_stream(process.stderr, stderr_buffer, is_stderr=True)
            )
            
            await process.wait()

            if process.returncode != 0:
                 error_msg = "".join(stderr_buffer)
                 return f"FAILURE: Qwen CLI exited with code {process.returncode}. Stderr: {error_msg}"

            # 5. Parse Result
            # Look for __ONEAGENT_RESULT__:<json>
            full_output = "".join(stdout_buffer)
            marker = "__ONEAGENT_RESULT__:"
            result_line = None
            
            for line in reversed(stdout_buffer):
                if marker in line:
                    result_line = line.strip()
                    break
            
            if not result_line:
                # Fallback: maybe the agent just outputted something without status tool?
                # But our bridge enforces it.
                return "FAILURE: Qwen CLI finished but did not return a structured result."
            
            json_str = result_line.split(marker, 1)[1]
            try:
                result = json.loads(json_str)
                status = result.get("status", "success")
                summary = result.get("summary", "No summary provided.")
                
                # 6. Return formatted status
                return f"Task Completed.\nStatus: {status}\nSummary: {summary}"
                
            except json.JSONDecodeError:
                return f"FAILURE: Failed to parse bridge result JSON: {json_str}"

        except Exception as e:
            return f"FAILURE: Exception running Qwen CLI bridge: {str(e)}"
