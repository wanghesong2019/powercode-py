"""创建或完整覆盖项目内文件的工具。"""

import json

from .path import resolve_in_work_dir
from .types import ToolError


def _parse_args(arguments_json: str) -> tuple[str, str]:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"write_file 参数不是合法 JSON：{exc}") from exc
    if not isinstance(args, dict):
        raise ToolError("工具参数必须是一个对象。")
    path = args.get("path")
    content = args.get("content")
    if not isinstance(path, str) or not isinstance(content, str):
        raise ToolError("path 和 content 必须是字符串。")
    return path, content


class WriteFileTool:
    name = "write_file"

    definition = {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "创建或完整覆盖当前项目中的文件，目录不存在时会自动创建。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对于项目根目录的路径"},
                    "content": {"type": "string", "description": "完整文件内容"},
                },
                "required": ["path", "content"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, work_dir):
        self.work_dir = work_dir

    def execute(self, arguments_json: str) -> str:
        path, content = _parse_args(arguments_json)
        target = resolve_in_work_dir(self.work_dir, path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return f"已写入文件：{path}"
