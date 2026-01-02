import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.core.registry import global_registry
from src.core.orchestrator import Orchestrator
from src.capabilities.agents.qwen_agent.agent import QwenBridgeAgent

async def main():
    print("--- Starting OneAgent Main Integration Test ---")
    
    # 1. Register QwenBridgeAgent
    # The Orchestrator picks up tools from the global registry.
    qwen_agent = QwenBridgeAgent()
    global_registry.register(qwen_agent)
    print(f"Registered Agent: {qwen_agent.name}")
    
    # Verify registration
    tools = global_registry.get_all_tool_schemas()
    print(f"Available Tools: {[t['function']['name'] for t in tools]}")
    
    # 2. Initialize Orchestrator
    orchestrator = Orchestrator(session_id="test-integration-001")
    
    # 3. Send Prompt
    # We explicitly ask for a coding task to trigger the Qwen Agent.
    prompt = "Please use the qwen_bridge_agent to create a file named 'hello_bridge.ts' with a console.log('Hello from Main Agent')."
    
    print(f"\nUser Prompt: {prompt}")
    print("\n--- Running Orchestrator ---")
    
    try:
        # We use run() which waits for the final answer, but we'll see logs streaming in stdout
        final_answer = await orchestrator.run(prompt)
        print("\n--- Final Answer ---")
        print(final_answer)
        
    except Exception as e:
        print(f"\nExecution Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
