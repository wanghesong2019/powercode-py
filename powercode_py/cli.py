"""powercode 命令行入口：注册工具并运行 Agent。"""

import argparse
import sys
from pathlib import Path

from .agent import Agent, AgentError
from .chat import ChatClient, ChatError
from .config import ConfigError, load_config
from .tools.bash import BashTool
from .tools.edit_file import EditFileTool
from .tools.read_file import ReadFileTool
from .tools.registry import Registry
from .tools.write_file import WriteFileTool


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：`powercode "你的问题"`，注册工具并运行 Agent。"""
    parser = argparse.ArgumentParser(
        prog="powercode",
        description="从零手搓的 AI Agent：一问一答，支持读、写、改文件与执行命令。",
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
        work_dir = Path.cwd().resolve()
        registry = Registry()
        registry.register(ReadFileTool(work_dir))
        registry.register(WriteFileTool(work_dir))
        registry.register(EditFileTool(work_dir))
        registry.register(BashTool(work_dir))
        agent = Agent(client, registry)

        print("AI 正在思考...\n")
        answer = agent.run(args.prompt)
    except (ConfigError, ChatError, AgentError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"AI：{answer}")
    return 0
