"""powercode 命令行入口：带 read_file 工具的一问一答。"""

import argparse
import sys

from .chat import ChatClient, ChatError
from .config import ConfigError, load_config
from .read_file import ReadFileError, read_file_tool


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：`powercode "你的问题"`，需要时读取项目文件后回答。"""
    parser = argparse.ArgumentParser(
        prog="powercode",
        description="从零手搓的 AI Agent：一问一答，支持读取项目文件。",
    )
    parser.add_argument("prompt", nargs="?", help="要发给模型的问题")
    parser.add_argument(
        "--provider",
        help="指定 provider.json 路径（默认按当前目录 → ~/.powercode/ 查找）",
    )
    args = parser.parse_args(argv)

    if not args.prompt:
        print('用法：powercode "你的问题"', file=sys.stderr)
        return 1

    try:
        config = load_config(args.provider)
        client = ChatClient(config)

        print("AI 正在思考...\n")

        first_message = client.ask_with_tools(args.prompt)
        tool_call = (
            first_message.tool_calls[0]
            if first_message and first_message.tool_calls
            else None
        )

        if not tool_call:
            content = first_message.content if first_message else None
            print(f"AI：{content or '模型没有返回内容。'}")
            return 0

        if tool_call.type != "function":
            print(f"错误：暂时不支持工具类型：{tool_call.type}", file=sys.stderr)
            return 1

        if tool_call.function.name != "read_file":
            print(f"错误：暂时不支持工具：{tool_call.function.name}", file=sys.stderr)
            return 1

        print(f"AI 想读文件：{tool_call.function.arguments}\n")

        file_content = read_file_tool(tool_call.function.arguments)
        answer = client.answer_after_read_file(args.prompt, tool_call, file_content)

        print(f"AI：{answer}")
        return 0
    except (ConfigError, ChatError, ReadFileError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1
