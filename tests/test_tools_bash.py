import json

import pytest

from powercode_py.tools.bash import BashTool, _decode_bytes
from powercode_py.tools.types import ToolError


def _args(command):
    return json.dumps({"command": command})


def test_bash_runs_command(tmp_path):
    tool = BashTool(work_dir=tmp_path)
    result = tool.execute(_args("echo hello"))
    assert "hello" in result


def test_bash_failing_command_raises(tmp_path):
    tool = BashTool(work_dir=tmp_path)
    with pytest.raises(ToolError, match="命令执行失败"):
        tool.execute(_args("this_command_does_not_exist_xyz_12345"))


def test_bash_requires_nonempty_command(tmp_path):
    tool = BashTool(work_dir=tmp_path)
    with pytest.raises(ToolError, match="非空字符串"):
        tool.execute(_args("   "))


def test_decode_bytes_utf8():
    assert _decode_bytes("中文".encode("utf-8")) == "中文"


def test_decode_bytes_gbk():
    # Windows 下 cmd 默认输出 GBK，即使系统 locale 不是 GBK 也要能还原中文。
    assert _decode_bytes("中文".encode("gbk")) == "中文"


def test_decode_bytes_never_crashes():
    # 不是任何已知编码的字节也要兜底返回字符串，而不是抛 UnicodeDecodeError。
    result = _decode_bytes(b"\xff\xfe\x00")
    assert isinstance(result, str)
