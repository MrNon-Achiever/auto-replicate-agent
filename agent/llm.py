"""
LLM调用模块
支持真正的工具调用循环
默认使用完整上下文，当token接近上限时自动压缩
"""

import json
import time
import tiktoken
from typing import Dict, List, Optional, Callable

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from . import config

# token上限阈值（90%时开始压缩）
TOKEN_THRESHOLD = 900000  # 900K tokens，留100K缓冲


def count_tokens(messages: List[Dict], model: str = "gpt-4") -> int:
    """
    计算消息列表的token数

    Args:
        messages: 消息列表
        model: 模型名称

    Returns:
        token总数
    """
    try:
        encoding = tiktoken.encoding_for_model(model)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")

    total_tokens = 0

    for message in messages:
        # 每条消息的基础token
        total_tokens += 4  # <|start|>role<|message|>content<|end|>

        # 内容token
        content = message.get("content", "")
        if content:
            total_tokens += len(encoding.encode(content))

        # 工具调用token
        tool_calls = message.get("tool_calls", [])
        if tool_calls:
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "")
                total_tokens += len(encoding.encode(name))
                total_tokens += len(encoding.encode(arguments))

        # 工具结果token
        if message.get("role") == "tool":
            total_tokens += len(encoding.encode(message.get("content", "")))

    return total_tokens


def compress_messages(messages: List[Dict], target_tokens: int = 500000) -> List[Dict]:
    """
    压缩消息列表，保留关键信息

    Args:
        messages: 原始消息列表
        target_tokens: 目标token数

    Returns:
        压缩后的消息列表
    """
    if len(messages) <= 10:
        return messages

    # 保留系统消息
    system_messages = [m for m in messages if m.get("role") == "system"]
    non_system_messages = [m for m in messages if m.get("role") != "system"]

    # 保留最近的消息
    keep_count = min(20, len(non_system_messages) // 2)
    recent_messages = non_system_messages[-keep_count:]

    # 创建摘要消息
    summary_parts = []
    for msg in non_system_messages[:-keep_count]:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "user" and len(content) < 200:
            summary_parts.append(f"用户: {content[:100]}")
        elif role == "assistant" and content:
            summary_parts.append(f"助手: {content[:100]}")
        elif role == "tool":
            try:
                result = json.loads(content)
                if not result.get("success", True):
                    summary_parts.append(f"工具错误: {result.get('error', '未知')[:100]}")
            except:
                pass

    summary = "\n".join(summary_parts[-10:])  # 只保留最近10条

    # 组合压缩后的消息
    compressed = system_messages + [
        {
            "role": "user",
            "content": f"[上下文压缩] 之前的对话摘要：\n{summary}\n\n请继续完成任务。"
        }
    ] + recent_messages

    return compressed


class LLMClient:
    """LLM客户端"""

    def __init__(self):
        """初始化LLM客户端"""
        self.client = None
        if HAS_OPENAI and config.OPENAI_API_KEY:
            self.client = OpenAI(
                api_key=config.OPENAI_API_KEY,
                base_url=config.OPENAI_API_BASE
            )

    def chat(
        self,
        messages: List[Dict],
        tools: List[Dict] = None,
        max_retries: int = 3
    ) -> Dict:
        """
        发送聊天请求（单次，不处理工具调用）

        Args:
            messages: 消息列表
            tools: 工具定义列表
            max_retries: 最大重试次数

        Returns:
            响应结果
        """
        if not self.client:
            return {
                "success": False,
                "error": "OpenAI客户端未初始化，请检查OPENAI_API_KEY环境变量"
            }

        # 计算token数
        token_count = count_tokens(messages, config.OPENAI_MODEL)

        # 日志：显示调用信息
        print(f"\n{'='*60}")
        print(f"[LLM] 发送请求")
        print(f"  模型: {config.OPENAI_MODEL}")
        print(f"  消息数: {len(messages)}")
        print(f"  工具数: {len(tools) if tools else 0}")
        print(f"  Token数: {token_count:,} / 1,000,000 ({token_count/1000000*100:.1f}%)")

        # 检查是否需要压缩
        if token_count > TOKEN_THRESHOLD:
            print(f"  ⚠️ Token接近上限，将自动压缩上下文")

        print(f"  最后一条消息: {messages[-1]['content'][:100]}..." if messages else "")
        print(f"{'='*60}")

        for attempt in range(max_retries):
            try:
                kwargs = {
                    "model": config.OPENAI_MODEL,
                    "messages": messages,
                    "max_tokens": config.MAX_TOKENS,
                    "temperature": config.TEMPERATURE
                }

                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                # 日志：显示重试信息
                if attempt > 0:
                    print(f"[LLM] 第 {attempt + 1} 次尝试...")

                response = self.client.chat.completions.create(**kwargs)

                # 提取响应内容
                message = response.choices[0].message

                result = {
                    "success": True,
                    "content": message.content or "",
                    "tool_calls": []
                }

                # 提取工具调用
                if message.tool_calls:
                    for tool_call in message.tool_calls:
                        result["tool_calls"].append({
                            "id": tool_call.id,
                            "type": "function",
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments
                            }
                        })

                # 日志：显示响应信息
                print(f"[LLM] 请求成功")
                print(f"  响应内容长度: {len(result['content'])} 字符")
                print(f"  工具调用数: {len(result['tool_calls'])}")
                if result['tool_calls']:
                    for tc in result['tool_calls']:
                        print(f"    - {tc['function']['name']}({tc['function']['arguments'][:50]}...)")
                print(f"{'='*60}\n")

                # 请求成功，等待一段时间避免频率限制
                time.sleep(1)
                return result

            except Exception as e:
                error_msg = str(e)

                # 日志：显示错误信息
                print(f"[LLM] 请求失败: {error_msg}")

                # 如果是429错误（频率限制），等待后重试
                if "429" in error_msg or "Too many requests" in error_msg:
                    wait_time = (attempt + 1) * 5  # 递增等待时间：5秒、10秒、15秒
                    print(f"[LLM] 请求频率限制，等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue

                # 其他错误直接返回
                return {
                    "success": False,
                    "error": f"LLM调用失败: {error_msg}"
                }

        # 所有重试都失败
        print(f"[LLM] 超过最大重试次数 ({max_retries})")
        print(f"{'='*60}\n")
        return {
            "success": False,
            "error": f"LLM调用失败: 超过最大重试次数 ({max_retries})"
        }

    def chat_with_tools(
        self,
        messages: List[Dict],
        tools: List[Dict],
        tool_executor: Callable,
        max_rounds: int = 10
    ) -> Dict:
        """
        带工具调用的聊天循环

        Args:
            messages: 消息列表
            tools: 工具定义列表
            tool_executor: 工具执行函数，接收(name, arguments) -> result
            max_rounds: 最大工具调用轮数

        Returns:
            最终响应结果
        """
        current_messages = messages.copy()
        round_count = 0

        # 日志：显示开始信息
        print(f"\n{'#'*60}")
        print(f"[工具调用] 开始工具调用循环")
        print(f"  最大轮数: {max_rounds}")
        print(f"{'#'*60}")

        while round_count < max_rounds:
            # 检查token数，必要时压缩
            token_count = count_tokens(current_messages, config.OPENAI_MODEL)
            if token_count > TOKEN_THRESHOLD:
                print(f"\n[上下文压缩] Token数 {token_count:,} 超过阈值 {TOKEN_THRESHOLD:,}")
                print(f"[上下文压缩] 正在压缩上下文...")
                current_messages = compress_messages(current_messages, target_tokens=500000)
                new_token_count = count_tokens(current_messages, config.OPENAI_MODEL)
                print(f"[上下文压缩] 压缩完成: {token_count:,} -> {new_token_count:,}")

            # 调用LLM
            response = self.chat(current_messages, tools)

            if not response["success"]:
                return response

            # 如果没有工具调用，说明LLM已经完成思考，返回结果
            if not response.get("tool_calls"):
                # 日志：显示完成信息
                print(f"\n{'#'*60}")
                print(f"[工具调用] 循环完成")
                print(f"  总轮数: {round_count}")
                print(f"  响应内容: {response['content'][:200]}...")
                print(f"{'#'*60}\n")
                return response

            # 有工具调用，需要执行
            round_count += 1

            # 日志：显示轮次信息
            print(f"\n{'-'*60}")
            print(f"[工具调用] 第 {round_count}/{max_rounds} 轮")
            print(f"  工具调用数: {len(response['tool_calls'])}")

            # 每轮工具调用后等待一段时间，避免频率限制
            time.sleep(2)

            # 将助手的回复（包含工具调用）添加到消息列表
            current_messages.append({
                "role": "assistant",
                "content": response["content"],
                "tool_calls": response["tool_calls"]
            })

            # 执行每个工具调用
            for tool_call in response["tool_calls"]:
                function_name = tool_call["function"]["name"]

                # 解析参数
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.JSONDecodeError:
                    arguments = {}

                # 日志：显示工具执行信息
                print(f"  执行工具: {function_name}")
                if arguments:
                    args_str = json.dumps(arguments, ensure_ascii=False)
                    print(f"    参数: {args_str[:100]}{'...' if len(args_str) > 100 else ''}")

                # 执行工具
                tool_result = tool_executor(function_name, arguments)

                # 日志：显示工具执行结果
                result_str = json.dumps(tool_result, ensure_ascii=False)
                print(f"    结果: {result_str[:100]}{'...' if len(result_str) > 100 else ''}")
                print(f"    成功: {tool_result.get('success', False)}")

                # 将工具结果添加到消息列表
                current_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "name": function_name,
                    "content": json.dumps(tool_result, ensure_ascii=False)
                })

            print(f"{'-'*60}")

        # 超过最大轮数，返回最后一次响应
        print(f"\n{'#'*60}")
        print(f"[工具调用] 达到最大轮数限制 ({max_rounds})")
        print(f"{'#'*60}\n")
        return {
            "success": True,
            "content": "工具调用轮数已达上限",
            "tool_calls": []
        }

    def is_available(self) -> bool:
        """检查LLM是否可用"""
        return self.client is not None


# 全局LLM客户端实例
_global_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局LLM客户端"""
    global _global_client
    if _global_client is None:
        _global_client = LLMClient()
    return _global_client
