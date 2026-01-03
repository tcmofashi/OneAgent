import sys
import asyncio
from src.core.orchestrator import Orchestrator

async def main():
    print("--- Run 1 ---")
    orc1 = Orchestrator()
    print(f"Session 1 ID: {orc1.session.session_id}")
    
    print("--- Run 2 ---")
    orc2 = Orchestrator()
    print(f"Session 2 ID: {orc2.session.session_id}")
    
    if orc1.session.session_id != orc2.session.session_id:
        print("SUCCESS: Session IDs are different.")
    else:
        print("FAILURE: Session IDs are the same.")

if __name__ == "__main__":
    asyncio.run(main())
