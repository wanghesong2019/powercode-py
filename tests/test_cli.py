from types import SimpleNamespace

from powercode_py import cli
from powercode_py.config import Config


class FakeChat:
    """模拟 ChatClient：ask_with_tools 返回给定消息，answer 返回固定文本。"""

    def __init__(self, first_message=None, answer="回答"):
        self._first_message = first_message
        self._answer = answer

    def ask_with_tools(self, prompt):
        return self._first_message

    def answer_after_read_file(self, prompt, tool_call, file_content):
        return self._answer


def _config():
    return Config(base_url="x", api_key="k", model="m")


def _message(content="直接回答", tool_calls=None):
    return SimpleNamespace(content=content, tool_calls=tool_calls)


def _tool_call(name="read_file", arguments='{"path":"README.md"}'):
    return SimpleNamespace(
        id="call_1",
        type="function",
        function=SimpleNamespace(name=name, arguments=arguments),
    )


def test_main_direct_answer(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    monkeypatch.setattr(
        cli,
        "ChatClient",
        lambda config, client=None: FakeChat(first_message=_message(content="直接回答")),
    )
    assert cli.main(["你好"]) == 0
    assert "直接回答" in capsys.readouterr().out


def test_main_read_file_flow(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    msg = _message(content=None, tool_calls=[_tool_call()])
    fake = FakeChat(first_message=msg, answer="这是一个教学项目")
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: fake)
    monkeypatch.setattr(cli, "read_file_tool", lambda args: "# powercode")

    assert cli.main(["读一下 README"]) == 0
    out = capsys.readouterr().out
    assert "AI 想读文件" in out
    assert "这是一个教学项目" in out


def test_main_without_prompt_prints_usage(capsys):
    assert cli.main([]) == 1
    assert "用法" in capsys.readouterr().err


def test_main_config_error_prints_stderr(capsys, monkeypatch):
    def boom(_path=None):
        raise cli.ConfigError("找不到配置文件 provider.json")

    monkeypatch.setattr(cli, "load_config", boom)
    assert cli.main(["你好"]) == 1
    err = capsys.readouterr().err
    assert "错误" in err and "找不到配置文件" in err


def test_main_chat_error_prints_stderr(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())

    def boom(config, client=None):
        raise cli.ChatError("认证失败")

    monkeypatch.setattr(cli, "ChatClient", boom)
    assert cli.main(["你好"]) == 1
    assert "认证失败" in capsys.readouterr().err


def test_main_read_file_error_prints_stderr(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    msg = _message(content=None, tool_calls=[_tool_call()])
    monkeypatch.setattr(
        cli, "ChatClient", lambda config, client=None: FakeChat(first_message=msg)
    )

    def boom(args):
        raise cli.ReadFileError("只能读取当前项目里的文件。")

    monkeypatch.setattr(cli, "read_file_tool", boom)
    assert cli.main(["读一下"]) == 1
    assert "只能读取当前项目里的文件" in capsys.readouterr().err


def test_main_forwards_provider_flag(capsys, monkeypatch):
    captured = {}

    def fake_load(path=None):
        captured["path"] = path
        return _config()

    monkeypatch.setattr(cli, "load_config", fake_load)
    monkeypatch.setattr(
        cli,
        "ChatClient",
        lambda config, client=None: FakeChat(first_message=_message(content="hi")),
    )
    assert cli.main(["--provider", "custom.json", "你好"]) == 0
    assert captured["path"] == "custom.json"
