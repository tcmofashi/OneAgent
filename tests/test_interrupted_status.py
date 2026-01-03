import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.capabilities.agents.qwen_agent.agent import QwenBridgeAgent

async def main():
    agent = QwenBridgeAgent()
    
    print("Testing INTERRUPTED status...")
    instruction = "You must use report_status tool with status='interrupted' and summary='Need upstream tool execute_http_request to fetch data'"
    
    try:
        result = await agent.execute(instruction)
        print("\n--- Execution Result ---")
        print(result)
        
        # Verify the result contains interrupted status
        if 'interrupted' in result.lower():
            print("\n✅ INTERRUPTED status correctly captured and returned!")
        else:
            print("\n⚠️ INTERRUPTED status NOT properly returned")
            
    except Exception as e:
        print(f"\nExecution Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
