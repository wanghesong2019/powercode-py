from powercode_py.context.session import Session


def test_append_and_get_history():
    s = Session()
    s.append({"role": "user", "content": "hi"})
    s.append({"role": "assistant", "content": "hello"})
    assert s.get_history() == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "hello"},
    ]


def test_get_history_returns_copy():
    s = Session()
    s.append({"role": "user", "content": "hi"})
    history = s.get_history()
    history.append({"role": "user", "content": "extra"})
    assert len(s.get_history()) == 1


def test_usage_snapshot():
    s = Session()
    s.append({"role": "user", "content": "hi"})
    s.save_usage(100)
    assert s.get_usage() == {"total_tokens": 100, "history_length": 1}


def test_compaction_state():
    s = Session()
    s.save_usage(100)
    s.save_compaction("摘要", 3)
    assert s.get_compaction() == {"summary": "摘要", "compacted_until": 3}
    # 压缩后 usage 应被清空
    assert s.get_usage() is None
