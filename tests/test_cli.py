from powercode_py import cli
from powercode_py.config import Config


class FakeChat:
    """模拟 ChatClient，返回固定文本。"""

    def __init__(self, text):
        self._text = text

    def complete(self, prompt):
        return self._text


def test_main_prints_reply(capsys, monkeypatch):
    monkeypatch.setattr(
        cli,
        "load_config",
        lambda _path="provider.json": Config(base_url="x", api_key="k", model="m"),
    )
    monkeypatch.setattr(cli, "ChatClient", lambda config, client=None: FakeChat("回复"))
    assert cli.main(["你好"]) == 0
    assert "回复" in capsys.readouterr().out


def test_main_without_prompt_prints_usage(capsys):
    assert cli.main([]) == 1
    assert "用法" in capsys.readouterr().err
