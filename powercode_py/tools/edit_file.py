"""精确替换文件内一段唯一文本的工具。"""

import json

from .path import resolve_in_work_dir
from .types import ToolError


def _parse_args(arguments_json: str) -> tuple[str, str, str]:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"edit_file 参数不是合法 JSON：{exc}") from exc
    if not isinstance(args, dict):
        raise ToolError("工具参数必须是一个对象。")
    path = args.get("path")
    old_text = args.get("old_text")
    new_text = args.get("new_text")
    if (
        not isinstance(path, str)
        or not isinstance(old_text, str)
        or not isinstance(new_text, str)
    ):
        raise ToolError("path、old_text 和 new_text 必须是字符串。")
    if not old_text:
        raise ToolError("old_text 不能为空。")
    return path, old_text, new_text


class EditFileTool:
    name = "edit_file"

    definition = {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": (
                "把文件中唯一出现的一段旧文本替换成新文本。修改前应先读取文件；"
                "如果 old_text 出现多次，请带上前后文后重试。"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "要修改的文件路径"},
                    "old_text": {"type": "string", "description": "文件中原有的完整文本"},
                    "new_text": {"type": "string", "description": "替换后的文本"},
                },
                "required": ["path", "old_text", "new_text"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, work_dir):
        self.work_dir = work_dir

    def execute(self, arguments_json: str) -> str:
        path, old_text, new_text = _parse_args(arguments_json)
        target = resolve_in_work_dir(self.work_dir, path)
        if not target.exists():
            raise ToolError(f"文件不存在：{path}")
        content = target.read_text(encoding="utf-8")
        matches = content.count(old_text)
        if matches == 0:
            raise ToolError("没有找到 old_text，请重新读取文件后再试。")
        if matches > 1:
            raise ToolError(f"old_text 出现了 {matches} 次，请提供包含前后文的更长文本。")
        target.write_text(content.replace(old_text, new_text), encoding="utf-8")
        return f"已修改文件：{path}"
