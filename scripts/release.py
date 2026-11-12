"""Work out the next release from the commits on ``main`` and prepare its changelog.

The release workflow runs this on every push to ``main``. It reads the
Conventional Commits made since the last ``vX.Y.Z`` tag and picks the bump:

- a breaking change (``feat!:``, ``fix(scope)!:`` or a ``BREAKING CHANGE:``
  footer) bumps the major version, or the minor version while we are at 0.x;
- ``feat`` bumps the minor version;
- ``fix`` and ``perf`` bump the patch version;
- anything else (``docs``, ``test``, ``ci``, ``chore``, ``refactor``, ...) does
  not release.

With no release tag yet, the first release is the version in ``pyproject.toml``
without its pre-release or dev suffix (``0.1.0.dev0`` gives ``0.1.0``).

Usage::

    python3 scripts/release.py next                # print the next version, or nothing
    python3 scripts/release.py changelog 0.2.0     # date the Unreleased section as 0.2.0
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
import subprocess
import sys
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_URL = "https://github.com/guilyx/beehave"

_HEADER = re.compile(r"^(?P<type>[A-Za-z]+)(?:\([^)]*\))?(?P<bang>!)?: (?P<subject>.+)$")
_BREAKING_FOOTER = re.compile(r"^BREAKING[ -]CHANGE: ", re.MULTILINE)
_RELEASE_TAG = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
_PYPROJECT_VERSION = re.compile(r'^version = "(\d+)\.(\d+)\.(\d+)[^"]*"$', re.MULTILINE)
_SEPARATOR = "\x1e"  # git log record separator, never in a commit message


class Bump(IntEnum):
    """How much a set of commits moves the version."""

    NONE = 0
    PATCH = 1
    MINOR = 2
    MAJOR = 3


@dataclass(frozen=True)
class Commit:
    """One Conventional Commit, reduced to what the release needs."""

    type: str
    subject: str
    breaking: bool

    @property
    def bump(self) -> Bump:
        """The bump this commit asks for on its own."""
        if self.breaking:
            return Bump.MAJOR
        if self.type == "feat":
            return Bump.MINOR
        if self.type in {"fix", "perf"}:
            return Bump.PATCH
        return Bump.NONE


Version = tuple[int, int, int]


def parse_commit(message: str) -> Commit | None:
    """Read a commit message; ``None`` when its first line is not a Conventional Commit."""
    header, _, body = message.strip().partition("\n")
    match = _HEADER.match(header.strip())
    if match is None:
        return None
    return Commit(
        type=match["type"].lower(),
        subject=match["subject"].strip(),
        breaking=bool(match["bang"]) or bool(_BREAKING_FOOTER.search(body)),
    )


def bump_of(commits: list[Commit]) -> Bump:
    """The largest bump asked for by any of the commits."""
    return max((c.bump for c in commits), default=Bump.NONE)


def next_version(current: Version, bump: Bump) -> Version:
    """Apply a bump. While the major version is 0, breaking changes bump the minor."""
    major, minor, patch = current
    if bump is Bump.MAJOR and major == 0:
        bump = Bump.MINOR
    if bump is Bump.MAJOR:
        return (major + 1, 0, 0)
    if bump is Bump.MINOR:
        return (major, minor + 1, 0)
    if bump is Bump.PATCH:
        return (major, minor, patch + 1)
    return current


def format_version(version: Version) -> str:
    """``(0, 2, 0)`` as ``0.2.0``."""
    return ".".join(str(part) for part in version)


# --------------------------------------------------------------------- git ---


def _git(*args: str, cwd: Path) -> str:
    result = subprocess.run(  # noqa: S603
        ["git", *args],  # noqa: S607
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout


def last_release(cwd: Path) -> tuple[str, Version] | None:
    """The highest ``vX.Y.Z`` tag reachable from HEAD, if any. Pre-release tags are ignored."""
    found: list[tuple[Version, str]] = []
    for tag in _git("tag", "--merged", "HEAD", "--list", "v*", cwd=cwd).split():
        match = _RELEASE_TAG.match(tag)
        if match:
            found.append(((int(match[1]), int(match[2]), int(match[3])), tag))
    if not found:
        return None
    version, tag = max(found)
    return tag, version


def commits_since(tag: str | None, cwd: Path) -> list[Commit]:
    """The Conventional Commits after ``tag`` (all of them without a tag), merges left out."""
    revision = f"{tag}..HEAD" if tag else "HEAD"
    log = _git("log", "--no-merges", f"--format=%B{_SEPARATOR}", revision, cwd=cwd)
    commits = (parse_commit(message) for message in log.split(_SEPARATOR))
    return [c for c in commits if c is not None]


def pyproject_version(cwd: Path) -> Version:
    """The release part of the version in ``pyproject.toml``."""
    match = _PYPROJECT_VERSION.search((cwd / "pyproject.toml").read_text(encoding="utf-8"))
    if match is None:
        msg = 'pyproject.toml has no `version = "X.Y.Z..."` line'
        raise ValueError(msg)
    return (int(match[1]), int(match[2]), int(match[3]))


def plan(cwd: Path) -> tuple[str | None, str | None, list[Commit]]:
    """``(next version, previous tag, commits)``; the version is ``None`` when nothing releases."""
    previous = last_release(cwd)
    tag = previous[0] if previous else None
    commits = commits_since(tag, cwd)
    bump = bump_of(commits)
    if bump is Bump.NONE:
        return None, tag, commits
    if previous is None:
        return format_version(pyproject_version(cwd)), None, commits
    return format_version(next_version(previous[1], bump)), tag, commits


# --------------------------------------------------------------- changelog ---

_UNRELEASED = "## [Unreleased]"
_SECTIONS = (
    ("Breaking changes", lambda c: c.breaking),
    ("Added", lambda c: not c.breaking and c.type == "feat"),
    ("Fixed", lambda c: not c.breaking and c.type in {"fix", "perf"}),
)


def notes_from_commits(commits: list[Commit]) -> str:
    """Release notes for when nobody wrote any under Unreleased."""
    blocks = []
    for title, keep in _SECTIONS:
        lines = [f"- {c.subject[:1].upper()}{c.subject[1:]}" for c in commits if keep(c)]
        if lines:
            blocks.append(f"### {title}\n\n" + "\n".join(lines))
    return "\n\n".join(blocks)


def release_changelog(
    text: str,
    version: str,
    previous_tag: str | None,
    commits: list[Commit],
    date: dt.date,
) -> str:
    """Turn ``## [Unreleased]`` into ``## [version] - date`` and update the links at the end.

    A fresh, empty Unreleased section goes above the release. If the Unreleased
    section was empty, its notes are written from the commits.
    """
    start = text.find(_UNRELEASED)
    if start < 0:
        msg = f"CHANGELOG.md has no '{_UNRELEASED}' heading"
        raise ValueError(msg)
    body_start = start + len(_UNRELEASED)
    end_match = re.compile(r"^(## |\[[^\]]+\]: )", re.MULTILINE).search(text, body_start)
    end = end_match.start() if end_match else len(text)
    body = text[body_start:end].strip() or notes_from_commits(commits)

    released = f"{_UNRELEASED}\n\n## [{version}] - {date.isoformat()}\n\n{body}\n\n"
    text = text[:start] + released + text[end:]

    compare = (
        f"{REPO_URL}/compare/{previous_tag}...v{version}"
        if previous_tag
        else f"{REPO_URL}/releases/tag/v{version}"
    )
    links = f"[Unreleased]: {REPO_URL}/compare/v{version}...HEAD\n[{version}]: {compare}"
    text, count = re.subn(r"^\[Unreleased\]: .*$", links, text, count=1, flags=re.MULTILINE)
    if count == 0:
        text = text.rstrip("\n") + "\n\n" + links
    return text.rstrip("\n") + "\n"


# --------------------------------------------------------------------- CLI ---


def main(argv: list[str] | None = None) -> int:
    """Entry point; see the module docstring."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("next", help="print the next version, or nothing if none is due")
    changelog = commands.add_parser("changelog", help="date the Unreleased section")
    changelog.add_argument("version")
    args = parser.parse_args(argv)

    version, previous_tag, commits = plan(args.root)
    if args.command == "next":
        if version:
            print(version)
        return 0

    path = args.root / "CHANGELOG.md"
    text = path.read_text(encoding="utf-8")
    today = dt.datetime.now(dt.timezone.utc).date()
    path.write_text(
        release_changelog(text, args.version, previous_tag, commits, today), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
