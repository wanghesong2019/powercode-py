"""powercode 命令行入口：运行 Agent。"""

import argparse
import sys

from .agent import Agent, AgentError
from .chat import ChatClient, ChatError
from .config import ConfigError, load_config


def main(argv: list[str] | None = None) -> int:
    """CLI 入口：`powercode "你的问题"`，运行 Agent 循环后回答。"""
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
        agent = Agent(client)

        print("AI 正在思考...\n")
        answer = agent.run(args.prompt)
    except (ConfigError, ChatError, AgentError) as exc:
        print(f"错误：{exc}", file=sys.stderr)
        return 1

    print(f"AI：{answer}")
    return 0
