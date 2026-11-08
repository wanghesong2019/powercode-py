"""封装 OpenAI 兼容 SDK，提供一问一答能力。"""

import openai
from openai import OpenAI

from .config import Config


class ChatError(Exception):
    """调用模型失败。"""


class ChatClient:
    """OpenAI 兼容客户端的一层薄封装。

    client 默认基于 config 构造 openai.OpenAI；测试时可注入假客户端。
    """

    def __init__(self, config: Config, client=None):
        self.config = config
        self.client = client or OpenAI(
            base_url=config.base_url,
            api_key=config.api_key,
        )

    def complete(self, prompt: str) -> str:
        """发送一句用户消息，返回模型回复文本。"""
        try:
            completion = self.client.chat.completions.create(
                model=self.config.model,
                messages=[{"role": "user", "content": prompt}],
            )
        except openai.AuthenticationError as exc:
            raise ChatError(
                f"认证失败，请检查 provider.json 里的 apiKey 是否正确：{exc}"
            ) from exc
        except openai.APIConnectionError as exc:
            raise ChatError(f"网络连接失败，请检查网络或 baseURL：{exc}") from exc
        except openai.APIError as exc:
            raise ChatError(f"调用模型失败：{exc}") from exc

        content = completion.choices[0].message.content
        return content or ""
