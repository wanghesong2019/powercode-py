"""Agent：把模型、工具注册中心、会话记忆串起来的核心循环。"""

from .chat import ChatClient
from .context.compactor import Compactor
from .context.session import Session
from .tools.registry import Registry

MAX_STEPS = 8

SYSTEM_PROMPT = (
    "你是 powercode-py，一个研发助手。请优先读取真实文件；修改后主动运行命令验证结果。请使用中文回答。"
)


class AgentError(Exception):
    """Agent 运行失败。"""


class Agent:
    """一个最小 Agent：循环调用模型，直到它不再申请工具。"""

    def __init__(self, client: ChatClient, registry: Registry, session: Session):
        self.client = client
        self.registry = registry
        self.session = session
        self.compactor = Compactor(client, client.get_context_window())

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
        self.session.append({"role": "user", "content": prompt})

        for step in range(1, MAX_STEPS + 1):
            memory = self.compactor.build_working_memory(self.session)
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                *memory,
            ]

            completion = self.client.complete_with_usage(
                messages,
                self.registry.get_definitions(),
            )
            message = completion.message

            if message is None:
                raise AgentError("模型没有返回消息。")

            self.session.append(self._assistant_message(message))

            if completion.total_tokens is not None and completion.total_tokens > 0:
                self.session.save_usage(completion.total_tokens)

            tool_calls = getattr(message, "tool_calls", None) or []
            if not tool_calls:
                return message.content or "模型没有返回文本内容。"

            for tool_call in tool_calls:
                if tool_call.type != "function":
                    raise AgentError(f"暂时不支持工具类型：{tool_call.type}")

                name = tool_call.function.name
                print(f"第 {step} 轮：AI 调用 {name}")

                try:
                    result = self.registry.execute(name, tool_call.function.arguments)
                    print(f"✓ {name} 执行完成\n")
                except Exception as exc:
                    result = f"工具执行失败：{exc}"
                    print(f"✗ {result}\n")

                self.session.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )

        raise AgentError(f"执行超过 {MAX_STEPS} 轮，已停止。")
