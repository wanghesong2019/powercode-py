"""读取项目内文本文件的工具。"""

import json

from .path import resolve_in_work_dir
from .types import ToolError

MAX_BYTES = 8_000


def _parse_path(arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"read_file 参数不是合法 JSON：{exc}") from exc
    if not isinstance(args, dict) or not isinstance(args.get("path"), str):
        raise ToolError("path 必须是字符串。")
    return args["path"]


class ReadFileTool:
    name = "read_file"

    definition = {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取当前项目中的文本文件。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对于项目根目录的文件路径"},
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, work_dir):
        self.work_dir = work_dir

    def execute(self, arguments_json: str) -> str:
        path = _parse_path(arguments_json)
        target = resolve_in_work_dir(self.work_dir, path)
        if not target.exists():
            raise ToolError(f"文件不存在：{path}")
        if target.is_dir():
            raise ToolError(f"这是一个目录，不是文件：{path}")
        data = target.read_bytes()
        if len(data) > MAX_BYTES:
            head = data[:MAX_BYTES].decode("utf-8", errors="replace")
            return f"{head}\n\n...[文件太长了，只返回前 {MAX_BYTES} 个字节]..."
        return data.decode("utf-8", errors="replace")
