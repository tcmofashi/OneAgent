import asyncio
import sys
from src.core.orchestrator import Orchestrator
from src.core.config import global_config
from src.utils.loader import load_capabilities

async def main():
    print("Initializing OneAgent...")
    
    # 1. Load Capabilities
    load_capabilities()
    
    # 2. Initialize Orchestrator
    orchestrator = Orchestrator()
    
    print(f"OneAgent initialized. Active Model: {global_config.get('llm.active_model_label')}")
    print("Enter 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue
                
            await orchestrator.run(user_input)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
