import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.capabilities.agents.qwen_agent.agent import QwenBridgeAgent

async def main():
    agent = QwenBridgeAgent()
    
    print("Testing report_status with result and reason parameters...")
    instruction = """
    Please fail this task intentionally. 
    Use report_status with:
    - status='FAILURE'
    - result='Intentional failure for testing'
    - reason='Testing the reason parameter'
    """
    
    try:
        result = await agent.execute(instruction)
        print("\n--- Execution Result ---")
        print(result)
        
        # Verify the result contains reason
        if 'Reason: Testing the reason parameter' in result:
            print("\n✅ Reason parameter correctly captured and returned!")
        else:
            print("\n⚠️ Reason parameter NOT properly returned")
            
    except Exception as e:
        print(f"\nExecution Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
