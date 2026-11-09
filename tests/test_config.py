from pathlib import Path

import pytest

from powercode_py.config import ConfigError, load_config


def test_load_valid_config(tmp_path):
    p = tmp_path / "provider.json"
    p.write_text(
        '{"baseURL":"https://api.deepseek.com","apiKey":"sk-test","model":"deepseek-v4-flash"}',
        encoding="utf-8",
    )
    c = load_config(p)
    assert (c.base_url, c.api_key, c.model) == (
        "https://api.deepseek.com",
        "sk-test",
        "deepseek-v4-flash",
    )


def test_missing_file(tmp_path):
    with pytest.raises(ConfigError, match="找不到配置文件"):
        load_config(tmp_path / "nope.json")


def test_malformed_json(tmp_path):
    p = tmp_path / "provider.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError, match="不是合法的 JSON"):
        load_config(p)


def test_missing_field(tmp_path):
    p = tmp_path / "provider.json"
    p.write_text('{"baseURL":"x"}', encoding="utf-8")
    with pytest.raises(ConfigError, match="字段缺失或不是非空字符串"):
        load_config(p)


def test_non_string_value_raises_config_error(tmp_path):
    p = tmp_path / "provider.json"
    p.write_text(
        '{"baseURL":"https://x","apiKey":"k","model":123}', encoding="utf-8"
    )
    with pytest.raises(ConfigError, match="字段缺失或不是非空字符串"):
        load_config(p)


def _write_provider(dirpath, model="deepseek-v4-flash"):
    p = dirpath / "provider.json"
    p.write_text(
        f'{{"baseURL":"https://api.deepseek.com","apiKey":"sk-test","model":"{model}"}}',
        encoding="utf-8",
    )
    return p


def test_load_config_no_arg_finds_cwd(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    _write_provider(tmp_path, model="cwd-model")

    assert load_config().model == "cwd-model"


def test_load_config_falls_back_to_home(tmp_path, monkeypatch):
    cwd = tmp_path / "empty"
    cwd.mkdir()
    home = tmp_path / "home"
    (home / ".powercode").mkdir(parents=True)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    _write_provider(home / ".powercode", model="home-model")

    assert load_config().model == "home-model"


def test_cwd_takes_priority_over_home(tmp_path, monkeypatch):
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    home = tmp_path / "home"
    (home / ".powercode").mkdir(parents=True)
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    _write_provider(cwd, model="cwd-model")
    _write_provider(home / ".powercode", model="home-model")

    assert load_config().model == "cwd-model"


def test_no_config_anywhere_lists_search_paths(tmp_path, monkeypatch):
    cwd = tmp_path / "empty"
    cwd.mkdir()
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.chdir(cwd)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    with pytest.raises(ConfigError) as excinfo:
        load_config()
    msg = str(excinfo.value)
    assert "provider.json" in msg
    assert ".powercode" in msg
