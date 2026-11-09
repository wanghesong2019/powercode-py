"""在项目目录内执行终端命令的工具。"""

import json
import subprocess

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
                text=True,
                timeout=TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired as exc:
            output = _truncate(_format_output(exc.stdout or "", exc.stderr or ""))
            if output:
                raise ToolError(f"命令执行超时：{command}\n\n{output}") from exc
            raise ToolError(f"命令执行超时：{command}") from exc

        if proc.returncode != 0:
            output = _truncate(_format_output(proc.stdout, proc.stderr))
            if output:
                raise ToolError(
                    f"命令执行失败（退出码 {proc.returncode}）\n\n{output}"
                )
            raise ToolError(f"命令执行失败（退出码 {proc.returncode}）")

        output = _truncate(_format_output(proc.stdout, proc.stderr))
        return output or "命令执行成功，没有终端输出。"
