#!/usr/bin/env python3
"""测试 ps aux 任务"""

import asyncio
import httpx
import time
import json


async def test_ps_task():
    async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
        resp = await client.post("http://localhost:8001/api/sessions")
        session_id = resp.json()["session_id"]
        print(f"Session: {session_id}")

        payload = {
            "message": "使用qwen_bridge_agent执行命令ps aux并统计进程数量，返回精确的数字",
            "session_id": session_id,
        }

        print(f"Starting task")
        start = time.time()

        resp = await client.post(
            "http://localhost:8001/api/chat/stream", json=payload, timeout=300.0
        )

        if resp.status_code == 200:
            result_text = ""
            current_event = ""
            line_count = 0
            for line in resp.iter_lines():
                line_count += 1
                if line.startswith("event:"):
                    current_event = line[6:].strip()
                    if current_event == "done":
                        break
                    continue
                if line.startswith("data:"):
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        if current_event == "message":
                            result_text += data
                        elif current_event == "step":
                            event_data = json.loads(data)
                            if event_data.get("type") == "answer_chunk":
                                content = event_data.get("content", "")
                                result_text += content
                                print(f"Chunk: {content[:50]}")
                            elif event_data.get("type") == "answer_done":
                                result_text += event_data.get("content", "")
                                print("Done!")
                    except:
                        pass

            elapsed = time.time() - start
            print(f"\nCompleted in {elapsed:.1f}s")
            print(f"Processed {line_count} lines")
            print(f"\nFinal result: {result_text}")
        else:
            print(f"Failed: {resp.status_code}")


if __name__ == "__main__":
    asyncio.run(test_ps_task())
