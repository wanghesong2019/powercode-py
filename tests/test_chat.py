from types import SimpleNamespace

import openai
import pytest

from powercode_py.chat import ChatClient, ChatError
from powercode_py.config import Config


def _completion(text):
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=text))]
    )


class FakeClient:
    """模拟 OpenAI 客户端：返回固定文本，或抛出指定异常。"""

    def __init__(self, text=None, error=None):
        self._text = text
        self._error = error

    @property
    def chat(self):
        def create(**kwargs):
            if self._error is not None:
                raise self._error
            return _completion(self._text)

        return SimpleNamespace(completions=SimpleNamespace(create=create))


def test_complete_returns_text():
    client = FakeClient(text="你好！")
    c = ChatClient(Config(base_url="https://x", api_key="k", model="m"), client=client)
    assert c.complete("hello") == "你好！"


def test_auth_error_raises_chat_error():
    resp = SimpleNamespace(
        request=SimpleNamespace(),
        status_code=401,
        headers={"x-request-id": "test-id"},
    )
    err = openai.AuthenticationError("invalid api key", response=resp, body=None)
    c = ChatClient(
        Config(base_url="https://x", api_key="k", model="m"), client=FakeClient(error=err)
    )
    with pytest.raises(ChatError):
        c.complete("hello")


def test_network_error_raises_chat_error():
    err = openai.APIConnectionError(request=None)
    c = ChatClient(
        Config(base_url="https://x", api_key="k", model="m"), client=FakeClient(error=err)
    )
    with pytest.raises(ChatError):
        c.complete("hello")


def test_timeout_error_mentions_timeout():
    err = openai.APITimeoutError(request=None)
    c = ChatClient(
        Config(base_url="https://x", api_key="k", model="m"), client=FakeClient(error=err)
    )
    with pytest.raises(ChatError, match="超时"):
        c.complete("hello")


def test_falsy_client_is_used():
    class FalsyClient:
        def __bool__(self):
            return False

        @property
        def chat(self):
            return SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kw: _completion("from falsy")
                )
            )

    c = ChatClient(
        Config(base_url="https://x", api_key="k", model="m"), client=FalsyClient()
    )
    assert c.complete("hello") == "from falsy"
