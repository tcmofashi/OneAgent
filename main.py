import asyncio
import sys
from src.core.orchestrator import Orchestrator
from src.core.config import global_config
from src.utils.loader import load_capabilities

async def main():
    print("Initializing OneAgent...")
    
    # 1. 加载能力
    # 1. Load Capabilities
    load_capabilities()
    
    # 2. 初始化 Orchestrator
    # 2. Initialize Orchestrator
    orchestrator = Orchestrator()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        prompt = sys.argv[1]
        print(f"Executing command: {prompt}")
        async for event in orchestrator.run_stream(prompt):
            event_type = event.get("type", "")
            if event_type == "answer_chunk":
                print(event.get("content", ""), end="", flush=True)
            elif event_type == "answer_done":
                print()
            elif event_type == "error":
                print(f"[Error] {event.get('content', '')}")
        return

    print(f"OneAgent initialized. Active Model: {global_config.get('llm.active_model_label')}")
    print("Enter 'exit' to quit.")
    
    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break
            
            if not user_input.strip():
                continue
            
            # 使用 run_stream 并显示流式事件
            print("\nAssistant: ", end="", flush=True)
            async for event in orchestrator.run_stream(user_input):
                event_type = event.get("type", "")
                
                if event_type == "thought":
                    print(f"\n[思考] {event.get('content', '')}")
                elif event_type == "tool_call":
                    print(f"\n[调用工具] {event.get('name', '')} - {event.get('args', {})}")
                elif event_type == "tool_result":
                    result = event.get('result', '')
                    print(f"\n[工具结果] {event.get('name', '')}: {result[:200]}...")
                elif event_type == "answer_chunk":
                    print(event.get("content", ""), end="", flush=True)
                elif event_type == "answer_done":
                    print()  # 换行
                elif event_type == "error":
                    print(f"\n[错误] {event.get('content', '')}")
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())

