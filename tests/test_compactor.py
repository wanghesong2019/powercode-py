from powercode_py.context.compactor import Compactor, truncate_large_tool_outputs
from powercode_py.context.session import Session


class _Msg:
    def __init__(self, content):
        self.content = content


class _Result:
    def __init__(self, message, total_tokens):
        self.message = message
        self.total_tokens = total_tokens


class _FakeClient:
    """提供 complete_with_usage 和 get_context_window 的假客户端。"""

    def __init__(self, summary="这是摘要"):
        self._summary = summary
        self.calls = []

    def get_context_window(self):
        return 128000

    def complete_with_usage(self, messages, tools):
        self.calls.append((messages, tools))
        return _Result(_Msg(self._summary), 123)


def test_small_context_not_compacted():
    session = Session()
    session.append({"role": "user", "content": "你好"})
    compactor = Compactor(_FakeClient(), 128000)
    memory = compactor.build_working_memory(session)
    assert memory == [{"role": "user", "content": "你好"}]
    assert session.get_compaction() is None


def test_large_context_compacted():
    client = _FakeClient("这是摘要")
    session = Session()
    big = "x" * 20000
    session.append({"role": "user", "content": "第一轮：请读大文件"})
    session.append({"role": "assistant", "content": big})
    session.append({"role": "user", "content": "第二轮：继续"})
    session.append({"role": "assistant", "content": "好的"})

    compactor = Compactor(client, max_context_tokens=2000, reserve_tokens=0, keep_recent_tokens=100)
    memory = compactor.build_working_memory(session)

    assert memory[0]["content"].startswith("[系统生成的较早会话摘要]")
    assert session.get_compaction()["summary"] == "这是摘要"
    # 近期消息应保留原文
    assert {"role": "user", "content": "第二轮：继续"} in memory
    assert {"role": "assistant", "content": "好的"} in memory


def test_truncate_large_tool_outputs():
    messages = [
        {"role": "tool", "tool_call_id": "c1", "content": "y" * 9000},
        {"role": "user", "content": "hi"},
    ]
    result = truncate_large_tool_outputs(messages)
    assert "已截断" in result[0]["content"]
    assert result[1] == {"role": "user", "content": "hi"}
