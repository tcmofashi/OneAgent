import json
import asyncio
from typing import List, Dict, Any, Optional
from src.core.llm import global_llm_client
from src.core.registry import global_registry
from src.capabilities.tools.todo_list import TodoListTool
from src.core.capability import BaseAgent
from src.core.compressor import global_compressor
from src.core.templates import get_template


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
        template = get_template("ORCHESTRATOR_SYSTEM")
        return template.format(
            todo_list=self.todo_list,
            capabilities_tree=global_registry.get_capabilities_tree_string()
        )

    async def run(self, user_input: str):
        """
        ReAct 循环的主入口点。
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
                                    
                                    # Get Upstream Tools (Orchestrator Capabilities)
                                    # For simplicity, we use the global capabilities tree as "Upstream View"
                                    upstream_view = global_registry.get_capabilities_tree_string()

                                    # Compress
                                    agent_desc = f"Name: {capability.name}\nDescription: {capability.description}"
                                    compression_result = await global_compressor.compress(
                                        history=self.history,
                                        target_task=instruction,
                                        agent_description=agent_desc,
                                        orchestrator_plan=self.todo_list,
                                        upstream_tools=upstream_view
                                    )
                                    
                                    # Update args (Injection)
                                    new_instruction = compression_result.get("core_request", instruction)
                                    compressed_context = compression_result.get("compressed_context", "")
                                    
                                    function_args["instruction"] = new_instruction
                                    function_args["context"] = compressed_context
                                    
                                    # --- TRUTHFUL DISPLAY ---
                                    print(f"\n{'='*20} PROMPT TO SUB-AGENT {'='*20}")
                                    print(f"Agent: {function_name}")
                                    print(f"Instruction (Refined): {new_instruction}")
                                    print(f"Context (Compressed): {compressed_context}")
                                    print(f"Upstream Tools Revealed: YES (Size: {len(upstream_view)} chars)")
                                    print(f"{'='*60}\n")
                            # ------------------------------------

                            result = await capability.execute(**function_args)
                            
                            # --- Handle Protocol Status ---
                            # Agents should return a status string like "[STATUS] Result..."
                            # We parse this to handle INTERRUPTED
                            if result.startswith("[INTERRUPTED]"):
                                print(f"\n[Orchestrator] Agent {function_name} requested INTERRUPTED.")
                                # In a real implementation, we would parse the specific request from 'result'
                                # E.g., "Requesting tool: get_system_info"
                                # For now, we treat it as a signal to plan for the requested tool in the NEXT turn.
                                # But to be effective, we should execute it NOW and re-invoke?
                                # Simplified approach: Return the interruption to the LLM so it can decide.
                                # The LLM will see: "Tool get_system_info requested..." and then calls it.
                                pass
                            # ------------------------------
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
