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
    with pytest.raises(ConfigError):
        load_config(tmp_path / "nope.json")


def test_malformed_json(tmp_path):
    p = tmp_path / "provider.json"
    p.write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)


def test_missing_field(tmp_path):
    p = tmp_path / "provider.json"
    p.write_text('{"baseURL":"x"}', encoding="utf-8")
    with pytest.raises(ConfigError):
        load_config(p)
