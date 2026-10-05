"""HTTP server for laya-mlx typed decision models."""

from typing import TYPE_CHECKING

__version__ = "0.1.0"
__all__ = ["Settings", "create_app", "__version__"]

if TYPE_CHECKING:
    from .app import create_app
    from .settings import Settings


def __getattr__(name: str):
    # Keep ``import laya_mlx_http`` cheap: the heavy MLX import only happens
    # when create_app/Settings are actually touched.
    if name == "create_app":
        from .app import create_app

        return create_app
    if name == "Settings":
        from .settings import Settings

        return Settings
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
