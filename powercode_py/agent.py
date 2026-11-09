"""Agent：把模型、工具、消息历史串起来的核心循环。"""

from .chat import ChatClient
from .read_file import read_file_tool

MAX_STEPS = 8

SYSTEM_PROMPT = (
    "你是 powercode-py，一个研发助手。需要了解项目内容时，优先读取真实文件。请使用中文回答。"
)


class AgentError(Exception):
    """Agent 运行失败。"""


class Agent:
    """一个最小 Agent：循环调用模型，直到它不再申请工具。"""

    def __init__(self, client: ChatClient):
        self.client = client

    def _assistant_message(self, message) -> dict:
        """把模型返回的消息转成可回传的 assistant 消息 dict。"""
        msg = {"role": "assistant", "content": message.content}
        tool_calls = getattr(message, "tool_calls", None) or []
        if tool_calls:
            msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in tool_calls
            ]
        return msg

    def run(self, prompt: str) -> str:
        """运行 Agent 循环，返回最终回答文本。"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ]

        for step in range(1, MAX_STEPS + 1):
            message = self.client.complete(messages)

            if message is None:
                raise AgentError("模型没有返回消息。")

            messages.append(self._assistant_message(message))

            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                return message.content or "模型没有返回文本内容。"

            for tool_call in tool_calls:
                if tool_call.type != "function":
                    raise AgentError(f"暂时不支持工具类型：{tool_call.type}")

                if tool_call.function.name != "read_file":
                    raise AgentError(f"暂时不支持工具：{tool_call.function.name}")

                print(f"第 {step} 轮：AI 想调用 read_file")
                print(f"正在读取文件：{tool_call.function.arguments}\n")

                try:
                    result = read_file_tool(tool_call.function.arguments)
                except Exception as exc:
                    result = f"读取失败：{exc}"

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        raise AgentError(f"执行超过 {MAX_STEPS} 轮，已停止。")
