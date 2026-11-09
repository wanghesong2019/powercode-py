from types import SimpleNamespace

import openai
import pytest

from powercode_py.chat import ChatClient, ChatError, CompletionResult
from powercode_py.config import Config


def _completion(message=None, content=None, total_tokens=None):
    if message is None:
        message = SimpleNamespace(content=content)
    usage = SimpleNamespace(total_tokens=total_tokens) if total_tokens is not None else None
    return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=usage)


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
    return Config(base_url="https://x", api_key="k", model="m", context_window=128000)


TOOLS = [{"type": "function", "function": {"name": "read_file"}}]


def test_complete_with_usage_returns_message_and_tokens():
    msg = SimpleNamespace(content="回答", tool_calls=None)
    client = FakeClient(response=_completion(msg, total_tokens=321))
    c = ChatClient(_config(), client=client)

    messages = [{"role": "user", "content": "hi"}]
    result = c.complete_with_usage(messages, TOOLS)

    assert isinstance(result, CompletionResult)
    assert result.message is msg
    assert result.total_tokens == 321
    kwargs = client.calls[0]
    assert kwargs["messages"] == messages
    assert kwargs["tools"] == TOOLS


def test_complete_with_usage_empty_choices():
    client = FakeClient(response=SimpleNamespace(choices=[], usage=None))
    c = ChatClient(_config(), client=client)
    result = c.complete_with_usage([], TOOLS)
    assert result.message is None
    assert result.total_tokens is None


def test_get_context_window():
    c = ChatClient(_config())
    assert c.get_context_window() == 128000


def test_auth_error_raises_chat_error():
    resp = SimpleNamespace(
        request=SimpleNamespace(), status_code=401, headers={"x-request-id": "test-id"}
    )
    err = openai.AuthenticationError("invalid api key", response=resp, body=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="认证失败"):
        c.complete_with_usage([], TOOLS)


def test_network_error_raises_chat_error():
    err = openai.APIConnectionError(request=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="网络连接失败"):
        c.complete_with_usage([], TOOLS)


def test_timeout_error_mentions_timeout():
    err = openai.APITimeoutError(request=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="超时"):
        c.complete_with_usage([], TOOLS)


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
    assert c.complete_with_usage([], TOOLS).message.content == "from falsy"
