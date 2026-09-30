"""launchd helpers that can be tested without touching the real launchd."""

from __future__ import annotations

import plistlib

import pytest

from laya_mlx_serve import Settings, launchd


def test_plist_payload_runs_module_with_flags():
    payload = launchd.plist_payload(
        Settings(host="0.0.0.0", port=9000, api_key="k", model_id="some/model", dtype="float32")
    )
    assert payload["Label"] == "laya-mlx-serve"
    assert payload["RunAtLoad"] is True
    assert payload["KeepAlive"] is True
    args = payload["ProgramArguments"]
    assert args[1:4] == ["-m", "laya_mlx_serve", "run"]
    assert "--host" in args and args[args.index("--host") + 1] == "0.0.0.0"
    assert args[args.index("--port") + 1] == "9000"
    assert args[args.index("--api-key") + 1] == "k"
    assert args[args.index("--model") + 1] == "some/model"
    # round-trips through plistlib without error
    assert plistlib.loads(plistlib.dumps(payload))["Label"] == "laya-mlx-serve"


def test_plist_payload_omits_api_key_when_unset():
    args = launchd.plist_payload(Settings())["ProgramArguments"]
    assert "--api-key" not in args


def test_install_refuses_lan_exposure_without_key():
    with pytest.raises(SystemExit, match="--api-key"):
        launchd.install(Settings(host="0.0.0.0"))
