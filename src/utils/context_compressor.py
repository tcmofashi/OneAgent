"""
Context Compression Utility
压缩对话历史以防止超出模型上下文限制
"""
from typing import List, Dict, Any
from src.core.llm import LLMClient
from src.core.config import global_config

# 配置常量
CONTEXT_CHAR_LIMIT = 90000  # 90k chars (90% of 100k)
KEEP_TURNS = 5  # 保留最近 5 轮对话


async def estimate_context_chars(messages: List[Dict[str, Any]]) -> int:
    """估算消息列表的总字符数"""
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(content)
        # 工具调用也计算在内
        if "tool_calls" in msg:
            total += len(str(msg["tool_calls"]))
    return total


async def compress_context(
    messages: List[Dict[str, Any]], 
    keep_turns: int = KEEP_TURNS,
    agent_name: str = "Agent"
) -> List[Dict[str, Any]]:
    """
    压缩对话历史，保留 system prompt + 最近 keep_turns 轮 + 压缩摘要
    
    Args:
        messages: 完整的消息历史
        keep_turns: 保留最近几轮对话 (1轮 = user + assistant)
        agent_name: Agent 名称用于日志
    
    Returns:
        压缩后的消息列表
    """
    # 检查是否需要压缩
    total_chars = await estimate_context_chars(messages)
    if total_chars <= CONTEXT_CHAR_LIMIT:
        return messages  # 不需要压缩
    
    print(f"[{agent_name}] 上下文压缩: {total_chars} chars -> 触发压缩...")
    
    # 分离 system prompt
    system_msg = None
    other_msgs = messages
    if messages and messages[0].get("role") == "system":
        system_msg = messages[0]
        other_msgs = messages[1:]
    
    # 计算保留多少条消息 (每轮大约 2-4 条消息: user, assistant, 可能有 tool/tool_result)
    # 保守估计每轮 4 条消息
    keep_count = keep_turns * 4
    
    if len(other_msgs) <= keep_count:
        return messages  # 消息不够多，不压缩
    
    # 分割: 需要压缩的部分 vs 保留的部分
    msgs_to_compress = other_msgs[:-keep_count]
    msgs_to_keep = other_msgs[-keep_count:]
    
    # 使用 compressor 模型压缩
    try:
        compressor_label = global_config.get("llm.functional_roles.compressor", "glm")
        compressor = LLMClient(target_model_label=compressor_label)
        
        # 构建压缩请求
        compress_content = "\n".join([
            f"[{m.get('role', 'unknown')}]: {str(m.get('content', ''))[:500]}..."  # 截断长内容
            for m in msgs_to_compress
        ])
        
        compress_prompt = f"""请将以下对话历史压缩成一个简洁的摘要（不超过500字）。
保留关键信息：任务目标、已完成的步骤、重要结果、当前状态。
删除冗余细节和重复内容。

对话历史:
{compress_content[:8000]}  # 限制输入长度

请输出压缩后的摘要:"""

        response = await compressor.chat_completion(
            messages=[{"role": "user", "content": compress_prompt}],
            stream=False
        )
        
        summary = response.content if hasattr(response, 'content') else str(response)
        
        # 构建压缩后的消息
        summary_msg = {
            "role": "user",
            "content": f"[系统摘要] 之前的对话内容已被压缩。关键信息:\n{summary}\n\n请继续当前任务。"
        }
        
        # 重建消息列表
        compressed_messages = []
        if system_msg:
            compressed_messages.append(system_msg)
        compressed_messages.append(summary_msg)
        compressed_messages.extend(msgs_to_keep)
        
        new_chars = await estimate_context_chars(compressed_messages)
        print(f"[{agent_name}] 上下文压缩完成: {total_chars} -> {new_chars} chars, {len(messages)} -> {len(compressed_messages)} msgs")
        
        return compressed_messages
        
    except Exception as e:
        print(f"[{agent_name}] 压缩失败: {e}，使用简单截断...")
        # 降级: 简单截断，只保留 system + 最近消息
        fallback = []
        if system_msg:
            fallback.append(system_msg)
        fallback.extend(msgs_to_keep)
        return fallback


async def should_compress(messages: List[Dict[str, Any]]) -> bool:
    """检查是否需要压缩"""
    total_chars = await estimate_context_chars(messages)
    return total_chars > CONTEXT_CHAR_LIMIT
