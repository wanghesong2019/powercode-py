from types import SimpleNamespace

import openai
import pytest

from powercode_py.chat import ChatClient, ChatError
from powercode_py.config import Config
from powercode_py.read_file import READ_FILE_TOOL


def _completion(message=None, content=None):
    if message is None:
        message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeClient:
    """记录 create 的调用参数，返回指定响应或抛出异常。"""

    def __init__(self, response=None, error=None):
        self._response = response
        self._error = error
        self.calls = []

    @property
    def chat(self):
        def create(**kwargs):
            self.calls.append(kwargs)
            if self._error is not None:
                raise self._error
            return self._response

        return SimpleNamespace(completions=SimpleNamespace(create=create))


def _config():
    return Config(base_url="https://x", api_key="k", model="m")


def test_complete_passes_messages_and_tools():
    msg = SimpleNamespace(content="回答", tool_calls=None)
    client = FakeClient(response=_completion(msg))
    c = ChatClient(_config(), client=client)

    messages = [{"role": "user", "content": "hi"}]
    result = c.complete(messages)

    assert result is msg
    kwargs = client.calls[0]
    assert kwargs["messages"] == messages
    assert kwargs["tools"] == [READ_FILE_TOOL]


def test_complete_empty_choices_returns_none():
    client = FakeClient(response=SimpleNamespace(choices=[]))
    c = ChatClient(_config(), client=client)
    assert c.complete([{"role": "user", "content": "hi"}]) is None


def test_auth_error_raises_chat_error():
    resp = SimpleNamespace(
        request=SimpleNamespace(), status_code=401, headers={"x-request-id": "test-id"}
    )
    err = openai.AuthenticationError("invalid api key", response=resp, body=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="认证失败"):
        c.complete([{"role": "user", "content": "hi"}])


def test_network_error_raises_chat_error():
    err = openai.APIConnectionError(request=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="网络连接失败"):
        c.complete([])


def test_timeout_error_mentions_timeout():
    err = openai.APITimeoutError(request=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="超时"):
        c.complete([])


def test_falsy_client_is_used():
    class FalsyClient:
        def __bool__(self):
            return False

        @property
        def chat(self):
            return SimpleNamespace(
                completions=SimpleNamespace(
                    create=lambda **kw: _completion(content="from falsy")
                )
            )

    c = ChatClient(_config(), client=FalsyClient())
    assert c.complete([]).content == "from falsy"
