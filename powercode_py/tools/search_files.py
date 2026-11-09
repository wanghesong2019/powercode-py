"""在工作目录内搜索文本的工具。"""

import json
from pathlib import Path

from .path import resolve_in_work_dir
from .types import ToolError

MAX_RESULTS = 50
MAX_FILE_BYTES = 200_000
SKIPPED_DIRECTORIES = {".git", ".powercode", "dist", "node_modules"}


def _parse_input(arguments_json: str) -> tuple[str, str]:
    try:
        args = json.loads(arguments_json)
    except json.JSONDecodeError as exc:
        raise ToolError(f"search_files 参数不是合法 JSON：{exc}") from exc
    if not isinstance(args, dict):
        raise ToolError("工具参数必须是对象。")
    query = args.get("query")
    if not isinstance(query, str) or not query.strip():
        raise ToolError("query 必须是非空字符串。")
    path = args.get("path", ".")
    if path is not None and not isinstance(path, str):
        raise ToolError("path 必须是字符串。")
    return query.strip(), (path if path is not None else ".")


class SearchFilesTool:
    name = "search_files"

    definition = {
        "type": "function",
        "function": {
            "name": "search_files",
            "description": "在当前项目的文本文件中搜索关键词。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要搜索的文本关键词"},
                    "path": {
                        "type": "string",
                        "description": "相对于项目根目录的搜索目录，默认是项目根目录",
                    },
                },
                "required": ["query"],
                "additionalProperties": False,
            },
        },
    }

    def __init__(self, work_dir):
        self.work_dir = Path(work_dir).resolve()

    def execute(self, arguments_json: str) -> str:
        query, path = _parse_input(arguments_json)
        start = resolve_in_work_dir(self.work_dir, path)
        lowered = query.lower()
        results = []

        def walk(directory: Path) -> None:
            if len(results) >= MAX_RESULTS:
                return
            for entry in directory.iterdir():
                if len(results) >= MAX_RESULTS:
                    return
                if entry.is_symlink():
                    continue
                if entry.is_dir() and entry.name in SKIPPED_DIRECTORIES:
                    continue
                if entry.is_dir():
                    walk(entry)
                    continue
                try:
                    if entry.stat().st_size > MAX_FILE_BYTES:
                        continue
                    content = entry.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if "\0" in content:
                    continue
                display = str(entry.relative_to(self.work_dir)).replace("\\", "/")
                for i, line in enumerate(content.splitlines(), start=1):
                    if lowered in line.lower():
                        results.append(f"{display}:{i}: {line.strip()}")
                    if len(results) >= MAX_RESULTS:
                        return

        walk(start)

        if not results:
            return f"没有找到关键词：{query}"
        suffix = f"\n...[最多返回 {MAX_RESULTS} 条结果]..." if len(results) >= MAX_RESULTS else ""
        return "\n".join(results) + suffix
