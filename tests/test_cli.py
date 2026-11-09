from powercode_py import cli
from powercode_py.config import Config


class FakeAgent:
    """模拟 Agent：run 返回固定回答或抛出异常。"""

    def __init__(self, answer="回答", error=None):
        self._answer = answer
        self._error = error

    def run(self, prompt):
        if self._error is not None:
            raise self._error
        return self._answer


def _config():
    return Config(base_url="x", api_key="k", model="m", context_window=128000)


def test_main_one_shot_prints_answer(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: object())
    monkeypatch.setattr(
        cli, "_build_agent", lambda client, work_dir, state, engine="handmade": FakeAgent(answer="直接回答")
    )
    assert cli.main(["你好"]) == 0
    assert "直接回答" in capsys.readouterr().out


def test_main_plan_flag(capsys, monkeypatch):
    captured = {}
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: object())

    def fake_build(client, work_dir, state, engine="handmade"):
        captured["mode"] = state.get_mode()
        return FakeAgent(answer="hi")

    monkeypatch.setattr(cli, "_build_agent", fake_build)
    assert cli.main(["--plan", "你好"]) == 0
    assert captured["mode"] == "plan"


def test_main_no_prompt_enters_interactive(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: object())
    monkeypatch.setattr(cli, "_build_agent", lambda client, work_dir, state, engine="handmade": FakeAgent())
    monkeypatch.setattr(cli, "_interactive_loop", lambda agent, state, work_dir: None)
    assert cli.main([]) == 0


def test_main_config_error_prints_stderr(capsys, monkeypatch):
    def boom(_path=None):
        raise cli.ConfigError("找不到配置文件 provider.json")

    monkeypatch.setattr(cli, "load_config", boom)
    assert cli.main(["你好"]) == 1
    assert "找不到配置文件" in capsys.readouterr().err


def test_main_agent_error_prints_stderr(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: object())
    monkeypatch.setattr(
        cli,
        "_build_agent",
        lambda client, work_dir, state, engine="handmade": FakeAgent(error=cli.AgentError("执行超过 30 轮")),
    )
    assert cli.main(["你好"]) == 1
    assert "执行超过 30 轮" in capsys.readouterr().err


def test_main_chat_error_prints_stderr(capsys, monkeypatch):
    monkeypatch.setattr(cli, "load_config", lambda _path=None: _config())

    def boom(config, client=None):
        raise cli.ChatError("认证失败")

    monkeypatch.setattr(cli, "ChatClient", boom)
    assert cli.main(["你好"]) == 1
    assert "认证失败" in capsys.readouterr().err


def test_main_forwards_provider_flag(capsys, monkeypatch):
    captured = {}

    def fake_load(path=None):
        captured["path"] = path
        return _config()

    monkeypatch.setattr(cli, "load_config", fake_load)
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: object())
    monkeypatch.setattr(cli, "_build_agent", lambda client, work_dir, state, engine="handmade": FakeAgent(answer="hi"))
    assert cli.main(["--provider", "custom.json", "你好"]) == 0
    assert captured["path"] == "custom.json"


def test_interactive_loop_exits_on_quit(monkeypatch):
    inputs = iter(["exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    cli._interactive_loop(FakeAgent(answer="hi"), cli.AgentState(), ".")
