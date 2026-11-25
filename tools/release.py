#!/usr/bin/env python3
"""Prepare a release: set the version and close the "Unreleased" section of the changelog.

Usage:
    python3 tools/release.py 0.2.0          # write the new version and the changelog heading
    python3 tools/release.py 0.2.0 --dry-run
    python3 tools/release.py --current      # print the current version

It edits two files, aad_docs/_version.py and CHANGELOG.md, and prints the commands that
commit, tag and push. It never commits, tags or pushes by itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
VERSION_FILE = ROOT / "aad_docs" / "_version.py"
CHANGELOG = ROOT / "CHANGELOG.md"

# PEP 440 subset the project allows: X.Y.Z with an optional aN, bN or rcN pre-release.
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)((?:a|b|rc)\d+)?$")
VERSION_LINE_RE = re.compile(r'^__version__ = "([^"]+)"$', re.MULTILINE)


def current_version() -> str:
    match = VERSION_LINE_RE.search(VERSION_FILE.read_text(encoding="utf-8"))
    if not match:
        raise SystemExit(f"No __version__ found in {VERSION_FILE}")
    return match.group(1)


def sort_key(version: str) -> tuple:
    major, minor, patch, pre = VERSION_RE.match(version).groups()
    order = {"a": 0, "b": 1, "rc": 2}
    if pre:
        kind = re.match(r"[a-z]+", pre).group(0)
        number = int(pre[len(kind):])
        pre_key = (order[kind], number)
    else:
        pre_key = (3, 0)  # a final release sorts after its pre-releases
    return (int(major), int(minor), int(patch), pre_key)


def release_notes(new: str, today: str, changelog: str) -> str:
    """Return the changelog with the Unreleased section renamed to the new version."""
    if re.search(rf"^## {re.escape(new)}\b", changelog, re.MULTILINE):
        raise SystemExit(f"CHANGELOG.md already has a section for {new}")
    marker = "## Unreleased"
    if marker not in changelog:
        raise SystemExit('CHANGELOG.md has no "## Unreleased" section')
    start = changelog.index(marker) + len(marker)
    next_heading = re.search(r"^## ", changelog[start:], re.MULTILINE)
    body = changelog[start : start + next_heading.start()] if next_heading else changelog[start:]
    if not body.strip():
        raise SystemExit('The "Unreleased" section of CHANGELOG.md is empty')
    return changelog.replace(marker, f"{marker}\n\n## {new} · {today}", 1)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("version", nargs="?", help="new version, such as 0.2.0 or 0.2.0rc1")
    parser.add_argument("--current", action="store_true", help="print the current version and exit")
    parser.add_argument("--dry-run", action="store_true", help="check everything and write nothing")
    args = parser.parse_args()

    old = current_version()
    if args.current:
        print(old)
        return 0
    if not args.version:
        parser.error("give the new version, or --current")

    new = args.version.removeprefix("v")
    if not VERSION_RE.match(new):
        raise SystemExit(f"{new!r} is not X.Y.Z with an optional aN, bN or rcN pre-release")
    # The same version is allowed once: the first release of the number that _version.py already holds.
    # release_notes() refuses it when the changelog already has that section.
    if new != old and sort_key(new) <= sort_key(old):
        raise SystemExit(f"{new} is not newer than the current version {old}")

    today = dt.date.today().isoformat()
    changelog = release_notes(new, today, CHANGELOG.read_text(encoding="utf-8"))
    version_text = VERSION_FILE.read_text(encoding="utf-8")
    version_text = VERSION_LINE_RE.sub(f'__version__ = "{new}"', version_text)

    if args.dry_run:
        print(f"Would change {old} to {new} and close the Unreleased section on {today}.")
        return 0

    VERSION_FILE.write_text(version_text, encoding="utf-8")
    CHANGELOG.write_text(changelog, encoding="utf-8")
    print(f"Version {old} -> {new}. Next:")
    print("  tools/check.sh && python3 -m pytest -q")
    print(f"  git commit -am 'chore(release): v{new}'")
    print(f"  git tag v{new}")
    print(f"  git push origin main v{new}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
