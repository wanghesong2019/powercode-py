"""失败分类、恢复提示与熔断记账。"""

import hashlib
import json
from dataclasses import dataclass

from ..tools.types import ToolError


class ToolExecutionError(ToolError):
    """带失败类型（kind）的工具执行错误。"""

    def __init__(self, kind: str, message: str):
        super().__init__(message)
        self.kind = kind


HINTS = {
    "edit_mismatch": "先 read_file 读取最新内容，再提取准确的 old_text；不要原样重复编辑。",
    "edit_ambiguous": "old_text 命中多处；读取文件并补充相邻上下文，确认唯一后再编辑。",
    "not_found": "先 list_files 或 search_files 确认真实路径，不要连续猜文件名。",
    "permission": "保留当前权限限制，向用户说明被拒绝的操作；不要换工具绕过，也不要自行提权。",
    "timeout": "先确认命令是否仍有进程或部分写入，再缩小验证范围；不要直接重跑或改成后台运行。",
    "output_limit": "输出超过缓冲区上限；先确认副作用，再缩小检查范围或改用摘要输出。",
    "command_failed": "根据退出状态和日志定位原因；检查脚本、依赖和语法后再决定是否重试。",
    "unknown": "原因尚未识别；保留原始错误，先做只读检查，无法确认时说明阻塞点。",
}


def classify_failure(name: str, error) -> str:
    """根据工具名和错误返回失败类型。"""
    if isinstance(error, ToolExecutionError):
        return error.kind
    message = str(error)
    if "当前模式不允许" in message or "只能操作当前项目" in message:
        return "permission"
    if "文件不存在" in message:
        return "not_found"
    if name == "edit_file" and "没有找到 old_text" in message:
        return "edit_mismatch"
    if name == "edit_file" and "old_text 出现了" in message:
        return "edit_ambiguous"
    return "unknown"


def _canonical(value):
    """递归排序 JSON 对象键，字符串/数组顺序不变。"""
    if isinstance(value, list):
        return [_canonical(item) for item in value]
    if isinstance(value, dict):
        return {k: _canonical(value[k]) for k in sorted(value)}
    return value


def call_key(name: str, args: str) -> str:
    """生成"工具名 + 规范化参数"的指纹。"""
    normalized = args
    try:
        normalized = json.dumps(_canonical(json.loads(args)), sort_keys=True)
    except (json.JSONDecodeError, TypeError):
        pass
    payload = json.dumps([name, normalized], ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass
class RecoveryDecision:
    kind: str
    count: int
    total_failures: int
    stop: bool
    output: str


class RecoveryManager:
    """两本账：单个调用失败次数 + 本次运行累计失败次数。"""

    def __init__(self):
        self._failures = {}
        self._total_failures = 0

    def on_success(self, name: str, args: str) -> None:
        self._failures.pop(call_key(name, args), None)

    def on_failure(self, name: str, args: str, error) -> RecoveryDecision:
        kind = classify_failure(name, error)
        key = call_key(name, args)
        count = self._failures.get(key, 0) + 1
        self._failures[key] = count
        self._total_failures += 1
        stop = kind == "permission" or count >= 3 or self._total_failures >= 6
        raw = str(error)[:4000]
        output = "\n".join(
            [
                f"工具执行失败：{raw}",
                f"[Harness 恢复提示] 类型：{kind}",
                HINTS[kind],
                f"同一调用失败 {count}/3 次；本次累计失败 {self._total_failures}/6 次。",
                "已暂停本次运行，未验证的 TODO 不能标为完成。"
                if stop
                else "请先检查原因，再决定下一步。",
            ]
        )
        return RecoveryDecision(
            kind=kind,
            count=count,
            total_failures=self._total_failures,
            stop=stop,
            output=output,
        )
