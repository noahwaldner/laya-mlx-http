"""launchd user-agent management so the server survives reboots (macOS only)."""

from __future__ import annotations

import os
import plistlib
import subprocess
import sys
from pathlib import Path
from typing import Sequence

from .settings import Settings

LABEL = "laya-mlx-http"
PLIST_PATH = Path.home() / "Library" / "LaunchAgents" / f"{LABEL}.plist"
LOG_PATH = Path.home() / "Library" / "Logs" / f"{LABEL}.log"


def _require_macos() -> None:
    if sys.platform != "darwin":
        raise SystemExit(f"launchd management requires macOS (got {sys.platform})")


def _domain() -> str:
    return f"gui/{os.getuid()}"


def _run(args: Sequence[str]) -> int:
    return subprocess.run(args, capture_output=True).returncode


def _launchctl(args: Sequence[str], fallback: Sequence[str] | None = None) -> int:
    code = _run(["launchctl", *args])
    if code != 0 and fallback is not None:
        code = _run(["launchctl", *fallback])
    return code


def plist_payload(settings: Settings) -> dict:
    """launchd plist that runs the server in the foreground with KeepAlive."""
    return {
        "Label": LABEL,
        "ProgramArguments": [
            sys.executable,
            "-m",
            "laya_mlx_http",
            "run",
            "--host",
            settings.host,
            "--port",
            str(settings.port),
            "--model",
            settings.model_id,
            "--dtype",
            settings.dtype,
            "--log-level",
            settings.log_level,
            *(["--api-key", settings.api_key] if settings.api_key else []),
        ],
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(LOG_PATH),
        "StandardErrorPath": str(LOG_PATH),
    }


def install(settings: Settings) -> int:
    _require_macos()
    if not settings.loopback_only and settings.api_key is None:
        raise SystemExit(
            f"refusing to install a {settings.host}-exposed agent without --api-key; "
            "anyone on your network would get unauthenticated access to the model"
        )
    PLIST_PATH.parent.mkdir(parents=True, exist_ok=True)
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLIST_PATH.write_bytes(plistlib.dumps(plist_payload(settings)))
    PLIST_PATH.chmod(0o600)  # the api key may be baked into ProgramArguments
    _launchctl(["bootout", f"{_domain()}/{LABEL}"])  # ignore: may not be loaded
    code = _launchctl(
        ["bootstrap", _domain(), str(PLIST_PATH)],
        fallback=["load", "-w", str(PLIST_PATH)],
    )
    if code != 0:
        raise SystemExit(f"launchd refused to load {PLIST_PATH}")
    print(f"installed {LABEL} ({PLIST_PATH})")
    print(f"  status: laya-mlx-http status")
    print(f"  logs:   laya-mlx-http logs   ({LOG_PATH})")
    return 0


def uninstall(settings: Settings) -> int:  # noqa: ARG001 - symmetric CLI signature
    _require_macos()
    _launchctl(["bootout", f"{_domain()}/{LABEL}"], fallback=["unload", "-w", str(PLIST_PATH)])
    PLIST_PATH.unlink(missing_ok=True)
    print(f"uninstalled {LABEL}")
    return 0


def start(settings: Settings) -> int:  # noqa: ARG001
    _require_macos()
    code = _launchctl(["kickstart", "-k", f"{_domain()}/{LABEL}"])
    if code != 0:
        raise SystemExit(f"{LABEL} is not loaded; run 'laya-mlx-http install' first")
    print(f"started {LABEL}")
    return 0


def stop(settings: Settings) -> int:  # noqa: ARG001
    _require_macos()
    code = _launchctl(["kill", "SIGTERM", f"{_domain()}/{LABEL}"])
    if code != 0:
        raise SystemExit(f"{LABEL} is not running (or not loaded)")
    print(f"stopped {LABEL}")
    return 0


def status(settings: Settings) -> int:  # noqa: ARG001
    _require_macos()
    if not PLIST_PATH.exists():
        print(f"not installed (no {PLIST_PATH})")
        return 1
    code = _run(["launchctl", "print", f"{_domain()}/{LABEL}"])
    if code == 0:
        print(f"running: {LABEL} ({settings.base_url})\nplist: {PLIST_PATH}\nlogs:  {LOG_PATH}")
    else:
        print(f"installed but not running: {LABEL}\nrun 'laya-mlx-http start'")
    return code


def logs(settings: Settings) -> int:  # noqa: ARG001
    if not LOG_PATH.exists():
        print(f"no log file yet ({LOG_PATH})")
        return 1
    return subprocess.run(["tail", "-n", "100", "-f", str(LOG_PATH)]).returncode
