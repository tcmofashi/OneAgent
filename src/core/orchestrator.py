import json
import asyncio
from typing import List, Dict, Any, Optional
from src.core.llm import global_llm_client
from src.core.registry import global_registry
from src.capabilities.tools.todo_list import TodoListTool
from src.core.capability import BaseAgent
from src.core.compressor import global_compressor

SYSTEM_PROMPT_TEMPLATE = """You are the OneAgent Orchestrator, a powerful AI assistant capable of managing and executing complex tasks using a variety of tools.

## Core Responsibilities
1. **Task Planning**: At the beginning of a complex request, break it down into a clear, numbered Task List using the `update_task_list` tool.
2. **Execution (ReAct)**: Execute tasks one by one.
3. **State Management**: You MUST keep the Task List updated. When a step is done, call `update_task_list` to mark it as checked.

## Current Task List
{todo_list}

## Format
Use the following thought process for every step:
- **Thought**: Analyze the current situation and the next task.
- **Action**: Decide to call a tool or provide the final answer.

## Instructions
- Always review the Context and History before acting.
- When calling tools, ensure arguments match the schema perfectly.
- **CRITICAL**: If the "Current Task List" above is empty or outdated, your FIRST action should be to call `update_task_list`.
"""

class Orchestrator:
    def __init__(self):
        self.todo_list = "(No tasks yet)"
        # Register internal tool manually or via registry special handling
        # For simplicity, we register it here but it needs to be available to LLM
        self.todo_tool = TodoListTool(self)
        global_registry.register(self.todo_tool)

    def update_todo_list(self, new_list: str):
        self.todo_list = new_list
        print(f"\n[Orchestrator] Task List Updated:\n{self.todo_list}\n")

    def _get_system_prompt(self) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(todo_list=self.todo_list)

    async def run(self, user_input: str):
        """
        Main entry point for the ReAct loop.
        """
        # Reset history for new run, or keep it? 
        # For a continuous session, we usually keep history but update system prompt.
        # Here we re-construct history with dynamic system prompt for every turn is complex with OpenAI API 
        # because System message is usually first. 
        # Strategy: We will maintain a list of messages, but we update the content of the first message (System) every time we call API.
        
        if not hasattr(self, 'history'):
             self.history = [{"role": "system", "content": self._get_system_prompt()}]
        
        # Update system prompt with latest todo list
        self.history[0]["content"] = self._get_system_prompt()

        # Add user input to history
        self.history.append({"role": "user", "content": user_input})
        
        while True:
            # 1. Update system prompt again just in case it changed in previous loop (unlikely but safe)
            self.history[0]["content"] = self._get_system_prompt()
            
            # 2. Get available tools
            tools = global_registry.get_all_tool_schemas()
            
            # 3. Call LLM
            print("\n[Orchestrator] Thinking...")

            response_message = await global_llm_client.chat_completion(
                messages=self.history,
                tools=tools if tools else None,
                tool_choice="auto" if tools else None
            )

            # 3. Handle response
            self.history.append(response_message)
            
            # Check for tool calls
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    function_name = tool_call.function.name
                    function_args = json.loads(tool_call.function.arguments)
                    
                    # Execute tool
                    capability = global_registry.get_capability(function_name)
                    if capability:
                        try:
                            # --- Interception for Code Agents ---
                            if isinstance(capability, BaseAgent):
                                instruction = function_args.get("instruction", "")
                                if instruction:
                                    print(f"\n[Orchestrator] Intercepting Agent Call: {function_name}...")
                                    print(f"[Orchestrator] Running Context Compressor...")
                                    
                                    # Compress
                                    agent_desc = f"Name: {capability.name}\nDescription: {capability.description}"
                                    compression_result = await global_compressor.compress(
                                        history=self.history,
                                        target_task=instruction,
                                        agent_description=agent_desc,
                                        orchestrator_plan=self.todo_list
                                    )
                                    
                                    # Update args
                                    new_instruction = compression_result.get("core_request", instruction)
                                    compressed_context = compression_result.get("compressed_context", "")
                                    
                                    function_args["instruction"] = new_instruction
                                    function_args["context"] = compressed_context
                                    
                                    # --- TRUTHFUL DISPLAY ---
                                    print(f"\n{'='*20} PROMPT TO SUB-AGENT {'='*20}")
                                    print(f"Agent: {function_name}")
                                    print(f"Instruction (Refined): {new_instruction}")
                                    print(f"Context (Compressed): {compressed_context}")
                                    print(f"{'='*60}\n")
                            # ------------------------------------

                            result = await capability.execute(**function_args)
                        except Exception as e:
                            result = f"Error executing {function_name}: {str(e)}"
                    else:
                        result = f"Error: Tool '{function_name}' not found."

                    # Append tool result to history
                    self.history.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result)
                    })
            else:
                # No tool calls -> Final Answer or Question
                content = response_message.content
                print(f"\n[Orchestrator] Final Answer: {content}")
                return content
