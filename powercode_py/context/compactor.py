"""上下文压缩器：生成"摘要 + 近期原文"的工作记忆。"""

import json

from .session import Session

SUMMARY_PROMPT = """你负责压缩一个 AI 编程任务的较早对话。
请只保留后续完成任务真正需要的信息，并严格使用以下结构：

## 用户目标
## 约束与关键决定
## 已完成
## 当前问题
## 已读取或修改的文件
## 下一步

不要编造对话中没有出现的结论。
"""


def estimate_message_tokens(message: dict) -> int:
    """粗略估算一条消息的 Token 数（UTF-8 字节数 ÷ 4，向上取整）。"""
    data = json.dumps(message, ensure_ascii=False)
    return (len(data.encode("utf-8")) + 3) // 4


def estimate_tokens(messages: list) -> int:
    """估算一批消息的总 Token 数。"""
    return sum(estimate_message_tokens(m) for m in messages)


def truncate_large_tool_outputs(messages: list) -> list:
    """截短超长的 tool 消息，保留开头和结尾（不修改原消息）。"""
    result = []
    for message in messages:
        if message.get("role") != "tool" or not isinstance(message.get("content"), str):
            result.append(message)
            continue
        content = message["content"]
        if len(content) <= 8000:
            result.append(message)
            continue
        result.append(
            {
                **message,
                "content": (
                    f"{content[:4000]}\n\n"
                    "...[中间工具输出已截断]...\n\n"
                    f"{content[-4000:]}"
                ),
            }
        )
    return result


def estimate_context_tokens(session: Session, history: list, current: list) -> int:
    """优先使用 API 返回的真实 usage，只估算 usage 之后新增的消息。"""
    usage = session.get_usage()
    if usage is None:
        return estimate_tokens(current)
    trailing = history[usage["history_length"]:]
    return usage["total_tokens"] + estimate_tokens(trailing)


class Compactor:
    """在请求模型前生成工作记忆：摘要 + 近期原文。"""

    def __init__(
        self,
        client,
        max_context_tokens: int,
        reserve_tokens: int = 16_384,
        keep_recent_tokens: int = 20_000,
    ):
        self.client = client
        self.max_context_tokens = max_context_tokens
        self.reserve_tokens = reserve_tokens
        self.keep_recent_tokens = keep_recent_tokens

    def build_working_memory(self, session: Session) -> list:
        history = session.get_history()
        state = session.get_compaction()
        start = state["compacted_until"] if state else 0
        summary = state["summary"] if state else None
        pending = history[start:]
        current = self._with_summary(summary, pending)
        usable_tokens = self.max_context_tokens - self.reserve_tokens
        context_tokens = estimate_context_tokens(session, history, current)

        if context_tokens <= usable_tokens:
            return current

        cut_index = self._find_cut_index(pending)
        if cut_index <= 0:
            return self._with_summary(summary, truncate_large_tool_outputs(pending))

        print(
            f"上下文接近上限（约 {context_tokens} / {usable_tokens} Token），正在压缩较早消息..."
        )

        older = truncate_large_tool_outputs(pending[:cut_index])
        recent = truncate_large_tool_outputs(pending[cut_index:])

        parts = []
        if summary:
            parts.append(f"# 上一次摘要\n{summary}")
        parts.append(f"# 新增历史\n{json.dumps(older, ensure_ascii=False, indent=2)}")
        summary_input = "\n\n".join(parts)

        completion = self.client.complete_with_usage(
            [
                {"role": "system", "content": SUMMARY_PROMPT},
                {"role": "user", "content": summary_input},
            ],
            [],
        )
        new_summary = ""
        if completion.message is not None:
            new_summary = (completion.message.content or "").strip()

        if not new_summary:
            return self._with_summary(summary, truncate_large_tool_outputs(pending))

        session.save_compaction(new_summary, start + cut_index)
        print("✓ 上下文压缩完成，近期消息继续保留原文。\n")
        return self._with_summary(new_summary, recent)

    def _find_cut_index(self, messages: list) -> int:
        recent_tokens = 0
        for index in range(len(messages) - 1, -1, -1):
            recent_tokens += estimate_message_tokens(messages[index])
            if recent_tokens < self.keep_recent_tokens:
                continue
            for cut in range(index, len(messages)):
                if messages[cut].get("role") == "user":
                    return cut
        return 0

    def _with_summary(self, summary, messages: list) -> list:
        if not summary:
            return messages
        summary_message = {
            "role": "user",
            "content": f"[系统生成的较早会话摘要]\n{summary}",
        }
        return [summary_message, *messages]
