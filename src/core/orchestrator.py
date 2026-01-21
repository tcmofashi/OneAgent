import json
import asyncio
import uuid
from typing import List, Dict, Any, Optional
from src.core.llm import global_llm_client
from src.core.registry import global_registry
from src.capabilities.tools.todo_list import TodoListTool
from src.capabilities.tools.agent_tasks import UpdateAgentTasksTool
from src.core.capability import BaseAgent
from src.core.compressor import global_compressor
from src.core.templates import get_template
from src.core.session import SessionManager
from src.core.logger import logger
from src.utils.context_compressor import compress_context, should_compress


class Orchestrator:
    def __init__(self, session_id: Optional[str] = None):
        self.session = SessionManager(session_id)

        # Hydrate state from session
        self.todo_list = self.session.task_list
        self.agent_tasks = self.session.agent_tasks

        # Register internal tool manually
        self.todo_tool = TodoListTool(self)
        self.agent_tasks_tool = UpdateAgentTasksTool(self)
        global_registry.register(self.todo_tool)
        global_registry.register(self.agent_tasks_tool)

        logger.log(
            event="SESSION_INIT",
            content={
                "session_id": self.session.session_id,
                "restored": self.session.loaded,
            },
            trace_id=self.session.trace_id,
        )

    def update_todo_list(self, new_list: str):
        self.todo_list = new_list
        self.session.update_task_list(new_list)
        logger.log("TASK_LIST_UPDATE", new_list, "Orchestrator", self.session.trace_id)
        print(f"\n[Orchestrator] Task List Updated:\n{self.todo_list}\n")

    def update_agent_tasks(self, new_list: str):
        self.agent_tasks = new_list
        self.session.update_agent_tasks(new_list)
        logger.log(
            "AGENT_TASKS_UPDATE", new_list, "Orchestrator", self.session.trace_id
        )
        print(f"\n[Orchestrator] Agent Task List Updated:\n{self.agent_tasks}\n")

    def _get_system_prompt(self) -> str:
        template = get_template("ORCHESTRATOR_SYSTEM")
        return template.format(
            todo_list=self.todo_list,
            agent_tasks=self.agent_tasks,
            capabilities_tree=global_registry.get_capabilities_tree_string(),
        )

    async def run_stream(self, user_input: str):
        """
        Streamable ReAct loop. Yields dict events.
        """
        # If history is empty, initialize system prompt
        if not self.session.history:
            self.session.add_history(
                {"role": "system", "content": self._get_system_prompt()}
            )

        # Update system prompt with latest todo list
        if self.session.history and self.session.history[0]["role"] == "system":
            self.session.history[0]["content"] = self._get_system_prompt()

        # Add user input
        self.session.add_history({"role": "user", "content": user_input})

        logger.log("USER_INPUT", user_input, "User", self.session.trace_id)
        yield {"type": "input_ack", "content": "Processing..."}

        while True:
            # 1. Update system prompt
            if self.session.history[0]["role"] == "system":
                self.session.history[0]["content"] = self._get_system_prompt()

            # 1.5. 上下文压缩检查
            if await should_compress(self.session.history):
                self.session.history = await compress_context(
                    self.session.history, keep_turns=5, agent_name="Orchestrator"
                )

            # 2. Tools (shared memory and file system tools are available to orchestrator and sub-agents)
            shared_memory_tool_names = [
                "memory_write",
                "memory_read",
                "memory_clear",
                "memory_info",
                "shared_save_to_file",
                "shared_read_file",
                "shared_list_files",
                "shared_delete_file",
            ]
            tools = global_registry.get_all_tool_schemas(
                whitelist=shared_memory_tool_names, exclude_runtime_tools=True
            )

            # 3. Call LLM
            print("\n[Orchestrator] Thinking...")
            span_id = str(uuid.uuid4())
            logger.log(
                "THOUGHT_START",
                {"history_len": len(self.session.history)},
                "Orchestrator",
                self.session.trace_id,
                span_id,
            )

            # Yield Thinking Event
            yield {"type": "thought", "content": "Thinking..."}

            # Call LLM with streaming
            stream_response = await global_llm_client.chat_completion(
                messages=self.session.history,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None,
                stream=True,
            )

            # Accumulators
            full_content = ""
            tool_calls_buffer = {}  # index -> tool_call_object

            async for chunk in stream_response:
                delta = chunk.choices[0].delta

                # 1. Content Streaming
                if delta.content:
                    content_chunk = delta.content
                    full_content += content_chunk
                    # 只打印非纯空白内容
                    if content_chunk.strip():
                        yield {"type": "answer_chunk", "content": content_chunk}

                # 2. Tool Call Streaming (Accumulation)
                if delta.tool_calls:
                    for tool_call_chunk in delta.tool_calls:
                        index = tool_call_chunk.index
                        if index not in tool_calls_buffer:
                            tool_calls_buffer[index] = {
                                "id": tool_call_chunk.id,
                                "function": {"name": "", "arguments": ""},
                            }

                        if tool_call_chunk.id:
                            tool_calls_buffer[index]["id"] = tool_call_chunk.id
                        if tool_call_chunk.function.name:
                            tool_calls_buffer[index]["function"]["name"] += (
                                tool_call_chunk.function.name
                            )
                        if tool_call_chunk.function.arguments:
                            tool_calls_buffer[index]["function"]["arguments"] += (
                                tool_call_chunk.function.arguments
                            )

            # Reconstruct Message Object for History
            # We need to construct a Mock Message object compatible with schema
            from openai.types.chat import (
                ChatCompletionMessage,
                ChatCompletionMessageToolCall,
            )
            from openai.types.chat.chat_completion_message_tool_call import Function

            reconstructed_tool_calls = []
            if tool_calls_buffer:
                for idx in sorted(tool_calls_buffer.keys()):
                    tc_data = tool_calls_buffer[idx]
                    reconstructed_tool_calls.append(
                        ChatCompletionMessageToolCall(
                            id=tc_data["id"]
                            or f"call_{uuid.uuid4()}",  # fallback if streamed id missing
                            function=Function(
                                name=tc_data["function"]["name"],
                                arguments=tc_data["function"]["arguments"],
                            ),
                            type="function",
                        )
                    )

            response_message = ChatCompletionMessage(
                role="assistant",
                content=full_content if full_content else None,
                tool_calls=reconstructed_tool_calls
                if reconstructed_tool_calls
                else None,
            )

            # 3. Handle response
            self.session.add_history(response_message.model_dump(exclude_none=True))

            # Check for tool calls
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name

                    # Clean and Parse Tool Call Arguments
                    raw_args = tool_call.function.arguments

                    # 清理重复的 JSON 对象问题 (某些模型如 glm 会产生 {"key": "value"}{} 这样的输出)
                    # Clean duplicated JSON objects (some models like glm produce {"key": "value"}{})
                    cleaned_args = raw_args.strip()
                    if cleaned_args.endswith("{}"):
                        cleaned_args = cleaned_args[:-2].strip()
                    # 处理多个重复的 {} 结尾
                    while cleaned_args.endswith("{}"):
                        cleaned_args = cleaned_args[:-2].strip()

                    function_args = None
                    try:
                        function_args = json.loads(cleaned_args)
                    except json.JSONDecodeError as e:
                        # 使用 LLM 清理模型尝试修复 JSON
                        # Use json_cleaner model to attempt fixing malformed JSON
                        print(
                            f"[Orchestrator] JSON parse failed, attempting LLM cleanup..."
                        )
                        try:
                            from src.core.config import global_config
                            from src.core.llm import LLMClient

                            json_cleaner_label = global_config.get(
                                "llm.functional_roles.json_cleaner"
                            )
                            cleaner = LLMClient(target_model_label=json_cleaner_label)
                            cleanup_prompt = f"""请修复以下损坏的 JSON 字符串，只返回有效的 JSON，不要添加任何解释：

损坏的 JSON:
```
{raw_args}
```

修复后的 JSON:"""
                            cleanup_response = await cleaner.chat_completion(
                                messages=[{"role": "user", "content": cleanup_prompt}],
                                stream=False,
                            )
                            cleaned_by_llm = cleanup_response.content.strip()
                            # 提取 JSON（可能被 markdown 代码块包裹）
                            if "```json" in cleaned_by_llm:
                                cleaned_by_llm = (
                                    cleaned_by_llm.split("```json")[1]
                                    .split("```")[0]
                                    .strip()
                                )
                            elif "```" in cleaned_by_llm:
                                cleaned_by_llm = (
                                    cleaned_by_llm.split("```")[1]
                                    .split("```")[0]
                                    .strip()
                                )

                            function_args = json.loads(cleaned_by_llm)
                            print(f"[Orchestrator] LLM cleanup successful")
                            logger.log(
                                "JSON_CLEANUP_SUCCESS",
                                {
                                    "original": raw_args[:100],
                                    "cleaned": cleaned_by_llm[:100],
                                },
                                "Orchestrator",
                                self.session.trace_id,
                                span_id,
                            )
                        except Exception as cleanup_error:
                            # LLM 清理也失败，记录错误并跳过
                            result = f"Error parsing tool arguments: {str(e)}. LLM cleanup also failed: {str(cleanup_error)}. Raw args: {raw_args[:200]}"
                            logger.log(
                                "TOOL_ERROR",
                                {
                                    "name": function_name,
                                    "error": str(e),
                                    "cleanup_error": str(cleanup_error),
                                },
                                "Orchestrator",
                                self.session.trace_id,
                                span_id,
                            )
                            yield {"type": "error", "content": result}
                            # MUST add tool result to history to maintain API consistency
                            self.session.add_history(
                                {
                                    "role": "tool",
                                    "tool_call_id": tool_call.id,
                                    "content": result,
                                }
                            )
                            continue  # Skip to next tool call

                    if function_args is None:
                        continue  # Skip if we still don't have valid args

                    logger.log(
                        "TOOL_CALL",
                        {"name": function_name, "args": function_args},
                        "Orchestrator",
                        self.session.trace_id,
                        span_id,
                    )
                    yield {
                        "type": "tool_call",
                        "name": function_name,
                        "args": function_args,
                    }

                    # Execute tool
                    capability = global_registry.get_capability(function_name)
                    result = None  # Initialize result

                    if capability:
                        try:
                            # --- Interception for Code Agents ---
                            if isinstance(capability, BaseAgent):
                                instruction = function_args.get("instruction", "")

                                # Validate required argument
                                if not instruction:
                                    error_msg = f"Error: Agent '{function_name}' requires an 'instruction' argument describing the task."
                                    logger.log(
                                        "TOOL_ERROR",
                                        {"name": function_name, "error": error_msg},
                                        "Orchestrator",
                                        self.session.trace_id,
                                        span_id,
                                    )
                                    yield {"type": "error", "content": error_msg}

                                    # Add to history
                                    self.session.add_history(
                                        {
                                            "role": "tool",
                                            "tool_call_id": tool_call.id,
                                            "content": error_msg,
                                        }
                                    )
                                    continue

                                if instruction:
                                    print(
                                        f"\n[Orchestrator] Intercepting Agent Call: {function_name}..."
                                    )

                                    agent_task_recorded = (
                                        function_name in self.agent_tasks
                                    )
                                    if not agent_task_recorded:
                                        error_msg = f"错误：在调用 {function_name} 之前，你必须先使用 `update_agent_tasks` 工具将任务记录在案。\n\n示例格式：\n- [ ] {function_name}: {instruction[:50]}...\n\n这样做是为了确保所有子任务都有明确的计划和跟踪。"
                                        logger.log(
                                            "AGENT_CALL_WITHOUT_TASK",
                                            {
                                                "agent": function_name,
                                                "instruction": instruction,
                                            },
                                            "Orchestrator",
                                            self.session.trace_id,
                                            span_id,
                                        )
                                        yield {"type": "error", "content": error_msg}

                                        self.session.add_history(
                                            {
                                                "role": "tool",
                                                "tool_call_id": tool_call.id,
                                                "content": error_msg,
                                            }
                                        )
                                        continue

                                    # Get Upstream Tools and Compress
                                    upstream_view = (
                                        global_registry.get_capabilities_tree_string()
                                    )
                                    agent_desc = f"Name: {capability.name}\nDescription: {capability.description}"

                                    # Yield compression start
                                    yield {
                                        "type": "thought",
                                        "content": f"Intercepting call to {function_name}. Compressing context...",
                                    }

                                    compression_result = (
                                        await global_compressor.compress(
                                            history=self.session.history,
                                            target_task=instruction,
                                            agent_description=agent_desc,
                                            orchestrator_plan=self.todo_list,
                                            upstream_tools=upstream_view,
                                        )
                                    )

                                    # Update args with standard sub-agent inputs
                                    new_instruction = compression_result.get(
                                        "core_request", instruction
                                    )
                                    compressed_context = compression_result.get(
                                        "compressed_context", ""
                                    )

                                    function_args["instruction"] = new_instruction
                                    function_args["context"] = compressed_context
                                    function_args["upstream_capabilities"] = (
                                        upstream_view  # 传递上级能力树
                                    )

                                    # Debug: Log parameter passing
                                    from src.core.capability import AgentPromptContext

                                    ctx = AgentPromptContext.from_legacy_params(
                                        instruction=new_instruction or instruction,
                                        context=compressed_context or "",
                                        upstream_capabilities=upstream_view,
                                        agent_name=function_name,
                                        agent_description=capability.description,
                                    )
                                    print(
                                        f"[Orchestrator] 参数传递调试信息:\n{ctx.get_summary()}"
                                    )

                                    # Log Interception
                                    logger.log(
                                        "AGENT_INTERCEPTION",
                                        {
                                            "original": instruction,
                                            "compressed": new_instruction,
                                        },
                                        "Orchestrator",
                                        self.session.trace_id,
                                        span_id,
                                    )

                                    print(
                                        f"\n{'=' * 20} PROMPT TO SUB-AGENT {'=' * 20}"
                                    )
                                    print(f"Instruction: {new_instruction}")
                                    print(f"{'=' * 60}\n")
                            # ------------------------------------

                            result = await capability.execute(**function_args)

                            # Log Result
                            logger.log(
                                "TOOL_RESULT",
                                {"name": function_name, "result": str(result)[:500]},
                                "Orchestrator",
                                self.session.trace_id,
                                span_id,
                            )
                            yield {
                                "type": "tool_result",
                                "name": function_name,
                                "result": str(result),
                            }

                        except Exception as e:
                            result = f"Error executing {function_name}: {str(e)}"
                            logger.log(
                                "TOOL_ERROR",
                                {"name": function_name, "error": str(e)},
                                "Orchestrator",
                                self.session.trace_id,
                                span_id,
                            )
                            yield {"type": "error", "content": str(e)}
                    else:
                        result = f"Error: Tool '{function_name}' not found."
                        logger.log(
                            "TOOL_ERROR",
                            {"name": function_name, "error": "Not Found"},
                            "Orchestrator",
                            self.session.trace_id,
                            span_id,
                        )
                        yield {
                            "type": "error",
                            "content": f"Tool {function_name} not found",
                        }

                    # ALWAYS append tool result to history (required by API)
                    self.session.add_history(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": str(result) if result else "No result",
                        }
                    )
            else:
                # No tool calls -> Check if there's actual content
                stripped_content = full_content.strip()
                if stripped_content:
                    # Final Answer
                    logger.log(
                        "TASK_END",
                        stripped_content,
                        "Orchestrator",
                        self.session.trace_id,
                        span_id,
                    )
                    print(f"\n[Orchestrator] Final Answer: {stripped_content}")
                    yield {"type": "answer_done", "content": stripped_content}
                    return
                else:
                    # Empty response - add a proper message sequence to continue
                    print(f"[Orchestrator] 空响应，尝试提示模型继续...")
                    # Add assistant empty message to maintain valid sequence
                    self.session.add_history({"role": "assistant", "content": ""})
                    # Add user prompt to encourage action
                    self.session.add_history(
                        {
                            "role": "user",
                            "content": "请继续执行任务，或者直接回复最终结果给用户。",
                        }
                    )
                    # Context compression is handled at loop start
                    continue

    async def run(self, user_input: str):
        """
        Legacy run method (wraps run_stream for backward compatibility).
        """
        final_answer = ""
        async for event in self.run_stream(user_input):
            if event["type"] == "answer":
                final_answer = event["content"]
        return final_answer
