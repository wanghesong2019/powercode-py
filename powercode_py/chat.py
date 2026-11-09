"""封装 OpenAI 兼容 SDK，提供单次模型请求能力。"""

from dataclasses import dataclass

import openai
from openai import OpenAI

from .config import Config


class ChatError(Exception):
    """调用模型失败。"""


@dataclass
class CompletionResult:
    """一次模型请求的结果：回复消息 + 真实 Token 用量。"""

    message: object
    total_tokens: int | None


class ChatClient:
    """OpenAI 兼容客户端的一层薄封装。

    client 默认基于 config 构造 openai.OpenAI；测试时可注入假客户端。
    """

    def __init__(self, config: Config, client=None, timeout: float = 60.0):
        self.config = config
        self.client = client if client is not None else OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
            timeout=timeout,
        )

    def get_context_window(self) -> int:
        """返回模型的上下文窗口上限。"""
        return self.config.context_window

    def _create(self, **kwargs):
        """调用 chat.completions.create，并把 SDK 异常翻译成 ChatError。"""
        try:
            return self.client.chat.completions.create(**kwargs)
        except openai.AuthenticationError as exc:
            raise ChatError(
                f"认证失败，请检查 provider.json 里的 apiKey 是否正确：{exc}"
            ) from exc
        except openai.APITimeoutError as exc:
            raise ChatError(f"请求超时，请稍后重试或检查网络：{exc}") from exc
        except openai.APIConnectionError as exc:
            raise ChatError(f"网络连接失败，请检查网络或 baseURL：{exc}") from exc
        except openai.APIError as exc:
            raise ChatError(f"调用模型失败：{exc}") from exc

    def complete_with_usage(self, messages, tools) -> CompletionResult:
        """把完整聊天记录和工具说明发给模型，返回消息与 Token 用量。"""
        completion = self._create(
            model=self.config.model,
            messages=messages,
            tools=tools,
        )
        message = completion.choices[0].message if completion.choices else None
        usage = getattr(completion, "usage", None)
        total_tokens = usage.total_tokens if usage is not None else None
        return CompletionResult(message=message, total_tokens=total_tokens)
