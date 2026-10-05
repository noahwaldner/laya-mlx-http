"""Runtime configuration for the laya-mlx-http HTTP API."""

from __future__ import annotations

from dataclasses import dataclass, replace

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_MODEL_ID = "aac6fef/laya-mlx"
DEFAULT_DTYPE = "float16"
DEFAULT_LOG_LEVEL = "info"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


@dataclass(frozen=True)
class Settings:
    """Server settings. Everything is explicit (CLI flags or arguments) —
    no environment variables or config files are read."""

    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    api_key: str | None = None
    model_id: str = DEFAULT_MODEL_ID
    dtype: str = DEFAULT_DTYPE
    log_level: str = DEFAULT_LOG_LEVEL

    @property
    def loopback_only(self) -> bool:
        return self.host in LOOPBACK_HOSTS

    @property
    def base_url(self) -> str:
        """Reachable base URL for humans (0.0.0.0 means "all interfaces")."""
        host = "127.0.0.1" if self.host in {"0.0.0.0", "::", "*"} else self.host
        return f"http://{host}:{self.port}"

    def with_overrides(self, **overrides: object) -> "Settings":
        """Return a copy, ignoring every override whose value is None."""
        return replace(self, **{k: v for k, v in overrides.items() if v is not None})
