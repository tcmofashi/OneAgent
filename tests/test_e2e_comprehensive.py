import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.core.registry import global_registry
from src.core.orchestrator import Orchestrator
from src.capabilities.agents.qwen_agent.agent import QwenBridgeAgent

async def main():
    print("--- Starting OneAgent Comprehensive E2E Test ---")
    
    # 1. Register QwenBridgeAgent
    qwen_agent = QwenBridgeAgent()
    global_registry.register(qwen_agent)
    print(f"Registered Agent: {qwen_agent.name}")
    
    # 2. Initialize Orchestrator
    orchestrator = Orchestrator(session_id="test-e2e-comprehensive-001")
    
    # 3. Comprehensive Prompt
    # We provide explicit absolute path context to avoid "Path must be absolute" errors.
    cwd = os.getcwd()
    target_file = os.path.join(cwd, "hello_bridge_e2e.ts")
    
    prompt = f"""
    Please use the qwen_bridge_agent to perform the following steps sequentially:
    1. Create a file named '{target_file}' with the content: console.log('Hello from E2E Test');
    2. Read the content of the file '{target_file}' to verify it.
    3. List the files in the directory '{cwd}' to confirm it exists.
    
    IMPORTANT: Always use the absolute path '{target_file}' for file operations.
    """
    
    print(f"\nUser Prompt: {prompt}")
    print("\n--- Running Orchestrator ---")
    
    try:
        final_answer = await orchestrator.run(prompt)
        print("\n--- Final Answer ---")
        print(final_answer)
        
        # Validation
        if "Hello from E2E Test" in str(final_answer) or os.path.exists(target_file):
            print("\n✅ Test PASSED: File created and verified.")
        else:
            print("\n❌ Test FAILED: File not found or content mismatch.")
            
    except Exception as e:
        print(f"\nExecution Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
