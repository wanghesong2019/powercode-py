import json

import pytest

from powercode_py.tools.bash import BashTool
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
