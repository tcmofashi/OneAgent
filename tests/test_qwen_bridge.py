import asyncio
import os
import sys

# Ensure src is in pythonpath
sys.path.append(os.getcwd())

from src.capabilities.agents.qwen_agent.agent import QwenBridgeAgent
from src.core.registry import global_registry

async def main():
    agent = QwenBridgeAgent()
    
    print("Running QwenBridgeAgent...")
    # Test a simple query that shouldn't require complex tools to verify basic connectivity
    # But wait, our bridge registers standard tools.
    # Let's ask it to just report status.
    instruction = "Please simply reply with 'Hello from Bridge' in your summary and mark status as success."
    
    try:
        result = await agent.execute(instruction)
        print("\n--- Execution Result ---")
        print(result)
    except Exception as e:
        print(f"\nExecution Failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
