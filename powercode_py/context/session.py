"""会话：保存同一进程内的完整消息历史与压缩状态。"""

from datetime import datetime


class Session:
    """按顺序保存消息，并记录 Token 用量与压缩进度。"""

    def __init__(self):
        self.created_at = datetime.now()
        self.updated_at = datetime.now()
        self._history = []
        self._compaction = None
        self._usage = None

    def append(self, *messages) -> None:
        """按顺序追加消息。"""
        self._history.extend(messages)
        self.updated_at = datetime.now()

    def get_history(self) -> list:
        """返回完整历史（列表浅拷贝，消息对象不会被内部改写）。"""
        return list(self._history)

    def get_compaction(self) -> dict | None:
        """返回压缩状态 {summary, compacted_until}，未压缩时为 None。"""
        return dict(self._compaction) if self._compaction is not None else None

    def get_usage(self) -> dict | None:
        """返回最近一次 Token 用量 {total_tokens, history_length}。"""
        return dict(self._usage) if self._usage is not None else None

    def save_usage(self, total_tokens: int) -> None:
        """保存最近一次请求的真实 Token 用量。"""
        self._usage = {
            "total_tokens": total_tokens,
            "history_length": len(self._history),
        }
        self.updated_at = datetime.now()

    def save_compaction(self, summary: str, compacted_until: int) -> None:
        """保存压缩结果，并清空旧的 usage 快照。"""
        self._compaction = {"summary": summary, "compacted_until": compacted_until}
        self._usage = None
        self.updated_at = datetime.now()
