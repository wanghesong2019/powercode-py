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


def _tool_call():
    return SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(name="read_file", arguments='{"path":"README.md"}'),
    )


def test_ask_with_tools_returns_message_and_passes_tools():
    msg = SimpleNamespace(content=None, tool_calls=[_tool_call()])
    client = FakeClient(response=_completion(msg))
    c = ChatClient(_config(), client=client)

    result = c.ask_with_tools("读一下 README")

    assert result is msg
    kwargs = client.calls[0]
    assert kwargs["tools"] == [READ_FILE_TOOL]
    assert kwargs["messages"][0]["role"] == "system"
    assert kwargs["messages"][1] == {"role": "user", "content": "读一下 README"}


def test_ask_with_tools_empty_choices_returns_none():
    client = FakeClient(response=SimpleNamespace(choices=[]))
    c = ChatClient(_config(), client=client)
    assert c.ask_with_tools("hi") is None


def test_answer_after_read_file_returns_text():
    client = FakeClient(response=_completion(content="这是一个从零手搓 AI Agent 的项目"))
    c = ChatClient(_config(), client=client)

    result = c.answer_after_read_file("这项目干嘛的", _tool_call(), "# powercode")

    assert result == "这是一个从零手搓 AI Agent 的项目"
    msgs = client.calls[0]["messages"]
    assert msgs[2] == {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": "call_1",
                "type": "function",
                "function": {"name": "read_file", "arguments": '{"path":"README.md"}'},
            }
        ],
    }
    assert msgs[3] == {"role": "tool", "tool_call_id": "call_1", "content": "# powercode"}


def test_answer_after_read_file_empty_returns_fallback():
    client = FakeClient(response=_completion(content=None))
    c = ChatClient(_config(), client=client)
    assert c.answer_after_read_file("hi", _tool_call(), "x") == "模型没有返回内容。"


def test_auth_error_raises_chat_error():
    resp = SimpleNamespace(
        request=SimpleNamespace(), status_code=401, headers={"x-request-id": "test-id"}
    )
    err = openai.AuthenticationError("invalid api key", response=resp, body=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="认证失败"):
        c.ask_with_tools("hello")


def test_network_error_raises_chat_error():
    err = openai.APIConnectionError(request=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="网络连接失败"):
        c.ask_with_tools("hello")


def test_timeout_error_mentions_timeout():
    err = openai.APITimeoutError(request=None)
    c = ChatClient(_config(), client=FakeClient(error=err))
    with pytest.raises(ChatError, match="超时"):
        c.ask_with_tools("hello")


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
    assert c.ask_with_tools("hello").content == "from falsy"
