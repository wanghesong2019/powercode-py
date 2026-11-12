"""在项目目录内执行终端命令的工具。"""

import json
import locale
import subprocess

from ..context.recovery import ToolExecutionError
from .types import ToolError

TIMEOUT_SECONDS = 30
MAX_OUTPUT = 8_000


def _parse_command(arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"bash 参数不是合法 JSON：{exc}") from exc
    command = args.get("command") if isinstance(args, dict) else None
    if not isinstance(command, str) or not command.strip():
        raise ToolError("command 必须是非空字符串。")
    return command.strip()


def _decode_bytes(data: bytes) -> str:
    """解码命令输出字节，兼容 Windows GBK 与 UTF-8 两种输出。

    Windows 下 cmd 默认按系统代码页（中文是 GBK）输出，而 git、python 等程序常
    输出 UTF-8；固定一种编码会撞上另一种，直接抛 UnicodeDecodeError。这里先按
    UTF-8 严格解码（能通过就基本是 UTF-8），失败再退回系统默认编码，再试 GBK，
    最后用 replace 兜底——保证任何输出都不会把整条命令搞崩。
    """
    if not data:
        return ""
    for encoding in ("utf-8", locale.getpreferredencoding(False), "gbk"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _format_output(stdout: str, stderr: str) -> str:
    return "\n".join(p for p in (stdout, stderr) if p).strip()


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT:
        return text[:MAX_OUTPUT] + f"\n...[输出太长，已截断到 {MAX_OUTPUT} 字符]..."
    return text


class BashTool:
    name = "bash"

    definition = {
        "type": "function",
        "function": {
            "name": "bash",
            "description": (
                "在当前项目目录中执行终端命令，用于构建、测试、运行代码和查看命令结果。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要执行的命令"},
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, work_dir):
        self.work_dir = work_dir

    def execute(self, arguments_json: str) -> str:
        command = _parse_command(arguments_json)
        try:
            proc = subprocess.run(
                command,
                shell=True,
                cwd=str(self.work_dir),
                capture_output=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            stdout = _decode_bytes(exc.stdout or b"")
            stderr = _decode_bytes(exc.stderr or b"")
            output = _truncate(_format_output(stdout, stderr))
            if output:
                raise ToolExecutionError("timeout", f"命令执行超时：{command}\n\n{output}") from exc
            raise ToolExecutionError("timeout", f"命令执行超时：{command}") from exc

        stdout = _decode_bytes(proc.stdout)
        stderr = _decode_bytes(proc.stderr)

        if proc.returncode != 0:
            output = _truncate(_format_output(stdout, stderr))
            if output:
                raise ToolExecutionError(
                    "command_failed", f"命令执行失败（退出码 {proc.returncode}）\n\n{output}"
                )
            raise ToolExecutionError("command_failed", f"命令执行失败（退出码 {proc.returncode}）")

        output = _truncate(_format_output(stdout, stderr))
        return output or "命令执行成功，没有终端输出。"
