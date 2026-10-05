from laya_mlx_http import Settings


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


def test_environment_is_ignored(monkeypatch):
    for key in (
        "LAYA_MLX_HOST",
        "LAYA_MLX_PORT",
        "LAYA_MLX_API_KEY",
        "LAYA_MLX_MODEL_ID",
        "LAYA_MLX_DTYPE",
        "LAYA_MLX_LOG_LEVEL",
    ):
        monkeypatch.setenv(key, "bogus")
    settings = Settings()
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000
    assert settings.api_key is None
    assert settings.model_id == "aac6fef/laya-mlx"
    assert settings.dtype == "float16"
    assert settings.log_level == "info"
