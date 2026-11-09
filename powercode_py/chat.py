"""封装 OpenAI 兼容 SDK，提供工具调用能力。"""

import openai
from openai import OpenAI

from .config import Config
from .read_file import READ_FILE_TOOL


class ChatError(Exception):
    """调用模型失败。"""


SYSTEM_PROMPT = (
    "你是 powercode-py，一个研发助手。需要了解项目内容时，优先读取真实文件。请使用中文回答。"
)

ANSWER_SYSTEM_PROMPT = (
    "你是 powercode-py，一个研发助手。请根据工具返回的真实文件内容，用中文回答用户。"
)


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

    def ask_with_tools(self, prompt: str):
        """向模型提问并声明 read_file 工具，返回首个消息（可能带 tool_calls）。"""
        completion = self._create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            tools=[READ_FILE_TOOL],
        )
        if not completion.choices:
            return None
        return completion.choices[0].message

    def answer_after_read_file(self, prompt: str, tool_call, file_content: str) -> str:
        """把读取到的文件内容喂回模型，返回最终回答文本。"""
        assistant_tool_call = {
            "id": tool_call.id,
            "type": tool_call.type,
            "function": {
                "name": tool_call.function.name,
                "arguments": tool_call.function.arguments,
            },
        }
        completion = self._create(
            model=self.config.model,
            messages=[
                {"role": "system", "content": ANSWER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [assistant_tool_call],
                },
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": file_content,
                },
            ],
        )
        if not completion.choices:
            return "模型没有返回内容。"
        message = completion.choices[0].message
        if message is None:
            return "模型没有返回内容。"
        return message.content or "模型没有返回内容。"
