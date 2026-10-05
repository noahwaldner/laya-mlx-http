#!/usr/bin/env python3
"""Keep the four version strings of this repo in sync (see RELEASING.md).

usage:
  scripts/versions.py check [vX.Y.Z]   verify all four match (and the tag if given)
  scripts/versions.py set X.Y.Z        write the version into all four files
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TARGETS: list[tuple[str, re.Pattern[str]]] = [
    ("python/pyproject.toml", re.compile(r'^version = "(?P<v>[^"]+)"', re.M)),
    (
        "python/src/laya_mlx_http/__init__.py",
        re.compile(r'^__version__ = "(?P<v>[^"]+)"', re.M),
    ),
    ("ai-provider/package.json", re.compile(r'"version":\s*"(?P<v>[^"]+)"')),
    ("ai-provider/src/version.ts", re.compile(r"VERSION = '(?P<v>[^']+)'")),
]


def read_all() -> list[tuple[str, str]]:
    found = []
    for rel, pattern in TARGETS:
        match = pattern.search((ROOT / rel).read_text(encoding="utf-8"))
        if match is None:
            sys.exit(f"error: no version string found in {rel}")
        found.append((rel, match.group("v")))
    return found


def check(tag: str | None) -> int:
    found = read_all()
    versions = {v for _, v in found}
    for rel, version in found:
        print(f"  {version:10} {rel}")
    if len(versions) != 1:
        print(f"error: versions disagree: {', '.join(sorted(versions))}", file=sys.stderr)
        return 1
    if tag is not None:
        want = tag.removeprefix("v")
        if versions != {want}:
            print(f"error: tag {tag} does not match package version {want}", file=sys.stderr)
            return 1
    print(f"ok: all four agree on {versions.pop()}")
    return 0


def set_version(new: str) -> int:
    if not re.fullmatch(r"\d+\.\d+\.\d+([-.\w]*)?", new):
        sys.exit(f"error: {new!r} does not look like a version (X.Y.Z)")
    for rel, pattern in TARGETS:
        path = ROOT / rel
        text = path.read_text(encoding="utf-8")
        match = pattern.search(text)
        if match is None:
            sys.exit(f"error: no version string found in {rel}")
        start, end = match.span("v")  # replace only the value, keep the syntax around it
        path.write_text(text[:start] + new + text[end:], encoding="utf-8")
        print(f"  {new:10} {rel}")
    print(f"ok: set version {new} in {len(TARGETS)} files")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p_check = sub.add_parser("check", help="verify all four versions agree")
    p_check.add_argument("tag", nargs="?", help="optional git tag (vX.Y.Z) to compare against")
    p_set = sub.add_parser("set", help="write a new version into all four files")
    p_set.add_argument("version", help="X.Y.Z")
    args = parser.parse_args(argv)
    if args.command == "check":
        return check(args.tag)
    return set_version(args.version)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
