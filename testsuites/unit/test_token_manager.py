from pathlib import Path

from testsuites.api_testing.framework.token_manager import TokenManager


class DummyConfig:
    def __init__(self, data):
        self.data = data

    def get(self, key, default=None):
        return self.data.get(key, default)


def test_apply_adds_auth_headers(monkeypatch, tmp_path):
    # Redirect cache paths to a temp directory to avoid touching real files
    cache_dir = tmp_path / "token_cache"
    monkeypatch.setattr("testsuites.api_testing.framework.token_manager.TOKEN_CACHE_DIR", cache_dir)
    monkeypatch.setattr(
        "testsuites.api_testing.framework.token_manager.TOKEN_CACHE_FILE",
        cache_dir / "cache.json",
    )
    monkeypatch.setattr(
        "testsuites.api_testing.framework.token_manager.TOKEN_LOCK_FILE",
        cache_dir / "cache.lock",
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    config = DummyConfig(
        {
            "security.api_key": "api-key-123",
            "auth.user_id": "demo_user",
            "auth.username": "demo_user",
            "auth.ttl": 120,
            "api.base_url": "http://localhost",
        }
    )

    TokenManager.reset()
    manager = TokenManager.instance(config)
    monkeypatch.setattr(manager, "_request_new_token", lambda: {"token": "t-123", "user": "demo", "ttl": 60})

    headers = manager.apply({})
    assert headers["Authorization"] == "Bearer t-123"
    assert headers["x-api-key"] == "api-key-123"
    assert "x-app-auth" in headers

    TokenManager.reset()

