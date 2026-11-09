"""递归列出项目内文件和目录的工具。"""

import json
from pathlib import Path

from .path import resolve_in_work_dir
from .types import ToolError

MAX_ITEMS = 200
SKIPPED_DIRECTORIES = {".git", ".powercode", "dist", "node_modules"}


def _parse_path(arguments_json: str) -> str:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"list_files 参数不是合法 JSON：{exc}") from exc
    if not isinstance(args, dict):
        raise ToolError("工具参数必须是对象。")
    path = args.get("path", ".")
    if path is not None and not isinstance(path, str):
        raise ToolError("path 必须是字符串。")
    return path if path is not None else "."


class ListFilesTool:
    name = "list_files"

    definition = {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "递归列出当前项目中的文件和目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "相对于项目根目录的目录，默认是当前项目根目录",
                    },
                },
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, work_dir):
        self.work_dir = Path(work_dir).resolve()

    def execute(self, arguments_json: str) -> str:
        start = resolve_in_work_dir(self.work_dir, _parse_path(arguments_json))
        items = []

        def walk(directory: Path) -> None:
            if len(items) >= MAX_ITEMS:
                return
            for entry in sorted(directory.iterdir(), key=lambda p: p.name):
                if len(items) >= MAX_ITEMS:
                    return
                if entry.is_symlink():
                    continue
                if entry.is_dir() and entry.name in SKIPPED_DIRECTORIES:
                    continue
                display = str(entry.relative_to(self.work_dir)).replace("\\", "/")
                items.append(f"{display}/" if entry.is_dir() else display)
                if entry.is_dir():
                    walk(entry)

        walk(start)

        if not items:
            return "目录为空。"
        suffix = f"\n...[最多返回 {MAX_ITEMS} 项]..." if len(items) >= MAX_ITEMS else ""
        return "\n".join(items) + suffix
