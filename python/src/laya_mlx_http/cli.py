"""Command line interface for laya-mlx-http."""

from __future__ import annotations

import argparse
import sys

from . import __version__
from .settings import Settings

COMMANDS = ("run", "install", "uninstall", "start", "stop", "status", "logs")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="laya-mlx-http",
        description="Serve laya-mlx typed decision models over HTTP.",
        epilog=(
            "With no command the server runs in the foreground. "
            "install/uninstall/start/stop/status/logs manage a macOS launchd "
            "user agent (no sudo)."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("command", nargs="?", choices=COMMANDS, default="run")
    parser.add_argument(
        "--host",
        help="bind address; default 127.0.0.1, use 0.0.0.0 to serve your LAN",
    )
    parser.add_argument("--port", type=int, help="port (default 8000)")
    parser.add_argument(
        "--api-key",
        help="require this key as X-API-Key on /v1/*; always set this for LAN exposure",
    )
    parser.add_argument("--model", help="HF model id or local checkpoint path")
    parser.add_argument("--dtype", help="float16 (default), float32 or bfloat16")
    parser.add_argument("--log-level", help="uvicorn log level (default info)")
    return parser


def _run_server(settings: Settings) -> int:
    if not settings.loopback_only and settings.api_key is None:
        print(
            f"warning: binding to {settings.host} without --api-key; "
            "anyone on the network can call /v1/predict",
            file=sys.stderr,
        )

    import uvicorn

    from .app import create_app

    print(f"server: {settings.base_url}  model: {settings.model_id}", flush=True)
    uvicorn.run(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        log_level=settings.log_level,
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = Settings().with_overrides(
        host=args.host,
        port=args.port,
        api_key=args.api_key,
        model_id=args.model,
        dtype=args.dtype,
        log_level=args.log_level,
    )

    if args.command == "run":
        return _run_server(settings)

    from . import launchd

    handlers = {
        "install": launchd.install,
        "uninstall": launchd.uninstall,
        "start": launchd.start,
        "stop": launchd.stop,
        "status": launchd.status,
        "logs": launchd.logs,
    }
    return handlers[args.command](settings)


if __name__ == "__main__":
    raise SystemExit(main())
