from jev_system_one.config import ConfigError, Settings


def test_settings_accept_jev_key(monkeypatch):
    monkeypatch.setenv("JEV_API_KEY", "jev-test")
    monkeypatch.setenv("OPENAI_API_KEY", "llm-test")
    settings = Settings.from_env()
    assert settings.jev_api_key == "jev-test"


def test_missing_jev_key(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("JEV_API_KEY", " ")
    monkeypatch.setenv("OPENAI_API_KEY", "llm-test")
    try:
        Settings.from_env()
    except ConfigError as exc:
        assert "JEV_API_KEY" in str(exc)
    else:
        raise AssertionError("expected ConfigError")
