import yaml

from testsuites.api_testing.framework.config_loader import ConfigLoader


def test_env_override_and_defaults(monkeypatch, tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.dump({"api": {"base_url": "http://example.com", "timeout": 10}}),
        encoding="utf-8",
    )

    ConfigLoader.reset()
    loader = ConfigLoader(config_path=config_path)
    assert loader.get("api.base_url") == "http://example.com"
    assert loader.get("api.retry_count", 3) == 3

    ConfigLoader.reset()
    monkeypatch.setenv("API_BASE_URL", "http://env.example.com")
    loader = ConfigLoader(config_path=config_path)
    assert loader.get("api.base_url") == "http://env.example.com"


def test_reload_updates_values(tmp_path):
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"api": {"timeout": 5}}), encoding="utf-8")

    ConfigLoader.reset()
    loader = ConfigLoader(config_path=config_path)
    assert loader.get("api.timeout") == 5

    config_path.write_text(yaml.dump({"api": {"timeout": 15}}), encoding="utf-8")
    loader.reload()
    assert loader.get("api.timeout") == 15

