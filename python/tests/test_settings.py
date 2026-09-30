from laya_mlx_serve import Settings


def test_defaults_are_loopback_only():
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.loopback_only
    assert settings.api_key is None
    assert settings.base_url == "http://127.0.0.1:8000"


def test_base_url_rewrites_wildcard_bind():
    assert Settings(host="0.0.0.0", port=9000).base_url == "http://127.0.0.1:9000"
    assert not Settings(host="0.0.0.0").loopback_only


def test_with_overrides_ignores_none():
    settings = Settings().with_overrides(host=None, port=9000, api_key=None)
    assert settings.host == "127.0.0.1"
    assert settings.port == 9000
    assert settings.api_key is None


def test_from_env(monkeypatch):
    monkeypatch.setenv("LAYA_MLX_HOST", "0.0.0.0")
    monkeypatch.setenv("LAYA_MLX_PORT", "9000")
    monkeypatch.setenv("LAYA_MLX_API_KEY", "hunter2")
    monkeypatch.setenv("LAYA_MLX_MODEL_ID", "some/model")
    monkeypatch.setenv("LAYA_MLX_DTYPE", "float32")
    settings = Settings.from_env()
    assert settings.host == "0.0.0.0"
    assert settings.port == 9000
    assert settings.api_key == "hunter2"
    assert settings.model_id == "some/model"
    assert settings.dtype == "float32"
