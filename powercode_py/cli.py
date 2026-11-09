"""powercode 命令行入口：注册工具并运行 Agent（支持交互循环）。"""

import argparse
import sys
from pathlib import Path

from .agent import Agent, AgentError
from .chat import ChatClient, ChatError
from .config import ConfigError, load_config
from .context.session import Session
from .tools.bash import BashTool
from .tools.edit_file import EditFileTool
from .tools.read_file import ReadFileTool
from .tools.registry import Registry
from .tools.write_file import WriteFileTool


def _build_agent(client, work_dir):
    """注册全部工具并创建一个带会话的 Agent。"""
    registry = Registry()
    registry.register(ReadFileTool(work_dir))
    registry.register(WriteFileTool(work_dir))
    registry.register(EditFileTool(work_dir))
    registry.register(BashTool(work_dir))
    session = Session()
    return Agent(client, registry, session)


def _interactive_loop(agent):
    """交互循环：持续读取输入，直到用户输入 exit/quit。"""
    print("已进入交互模式，输入 exit 或 quit 退出。\n")
    while True:
        try:
            value = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not value:
            continue
        if value in ("exit", "quit"):
            break
        try:
            print("AI 正在思考...\n")
            answer = agent.run(value)
            print(f"AI：{answer}")
        except (ChatError, AgentError) as exc:
            print(f"本轮执行失败：{exc}")


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：`powercode "你的问题"` 单次执行，不带参数则进入交互模式。"""
    parser = argparse.ArgumentParser(
        prog="powercode",
        description="从零手搓的 AI Agent：一问一答，支持读、写、改文件与执行命令。",
    )
    parser.add_argument("prompt", nargs="?", help="要发给模型的问题；不传则进入交互模式")
    parser.add_argument(
        "--provider",
        help="指定 provider.json 路径（默认按当前目录 → ~/.powercode/ 查找）",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.provider)
        client = ChatClient(config)
        agent = _build_agent(client, Path.cwd().resolve())
    except (ConfigError, ChatError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    if args.prompt:
        try:
            print("AI 正在思考...\n")
            answer = agent.run(args.prompt)
        except (ChatError, AgentError) as exc:
            print(f"错误：{exc}", file=sys.stderr)
            return 1
        print(f"AI：{answer}")
        return 0

    _interactive_loop(agent)
    return 0
