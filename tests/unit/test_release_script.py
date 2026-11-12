"""``scripts/release.py``: the next version from Conventional Commits, and the changelog."""

from __future__ import annotations

import datetime as dt
import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    path = ROOT / "scripts" / "release.py"
    spec = importlib.util.spec_from_file_location("beehave_release_script", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses look their module up here
    spec.loader.exec_module(module)
    return module


REL: Any = _load()


# ------------------------------------------------------------ commit rules ---


@pytest.mark.parametrize(
    ("message", "bump"),
    [
        ("feat: read v4 trees", "MINOR"),
        ("feat(cli): a diff command", "MINOR"),
        ("fix: portable paths", "PATCH"),
        ("perf(walk): cache subtrees", "PATCH"),
        ("docs: a guide", "NONE"),
        ("chore(release): 0.1.0", "NONE"),
        ("refactor!: rename the API", "MAJOR"),
        ("feat(api)!: drop analyze()", "MAJOR"),
        ("fix: x\n\nBREAKING CHANGE: the JSON schema changed", "MAJOR"),
        ("fix: x\n\nBREAKING-CHANGE: the JSON schema changed", "MAJOR"),
    ],
)
def test_each_commit_type_asks_for_its_bump(message: str, bump: str) -> None:
    commit = REL.parse_commit(message)

    assert commit is not None
    assert commit.bump is REL.Bump[bump]


@pytest.mark.parametrize(
    "message", ["Merge pull request #13 from x/y", "Update README.md", "feat:no space"]
)
def test_other_messages_are_not_conventional_commits(message: str) -> None:
    assert REL.parse_commit(message) is None


def test_the_largest_bump_wins() -> None:
    commits = [REL.parse_commit(m) for m in ("docs: a", "fix: b", "feat: c", "test: d")]

    assert REL.bump_of(commits) is REL.Bump.MINOR
    assert REL.bump_of([]) is REL.Bump.NONE


@pytest.mark.parametrize(
    ("current", "bump", "expected"),
    [
        ((1, 2, 3), "MAJOR", (2, 0, 0)),
        ((1, 2, 3), "MINOR", (1, 3, 0)),
        ((1, 2, 3), "PATCH", (1, 2, 4)),
        ((1, 2, 3), "NONE", (1, 2, 3)),
        # While at 0.x, a breaking change is a minor release.
        ((0, 4, 1), "MAJOR", (0, 5, 0)),
    ],
)
def test_next_version(current: tuple[int, int, int], bump: str, expected: tuple[int, ...]) -> None:
    assert REL.next_version(current, REL.Bump[bump]) == expected


# ------------------------------------------------------------- git history ---


def _git(repo: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
    )


def _commit(repo: Path, message: str) -> None:
    _git(repo, "commit", "--allow-empty", "-q", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "-q")
    (tmp_path / "pyproject.toml").write_text('[project]\nversion = "0.1.0.dev0"\n')
    _git(tmp_path, "add", ".")
    _commit(tmp_path, "chore: start")
    return tmp_path


def test_without_a_tag_the_first_release_is_the_pyproject_version(repo: Path) -> None:
    _commit(repo, "feat: something")

    version, previous, commits = REL.plan(repo)

    assert version == "0.1.0"
    assert previous is None
    assert [c.subject for c in commits] == ["something", "start"]


def test_only_commits_after_the_last_release_count(repo: Path) -> None:
    _commit(repo, "feat!: big change")
    _git(repo, "tag", "v0.1.0")
    _git(repo, "tag", "v0.2.0rc1")  # pre-releases are not a base
    _commit(repo, "docs: words")
    _commit(repo, "fix: a bug\n\nWith a body.")

    version, previous, commits = REL.plan(repo)

    assert version == "0.1.1"
    assert previous == "v0.1.0"
    assert [c.subject for c in commits] == ["a bug", "words"]


def test_nothing_releases_without_a_feat_or_a_fix(repo: Path) -> None:
    _git(repo, "tag", "v1.0.0")
    _commit(repo, "ci: faster")
    _commit(repo, "docs: typo")

    assert REL.plan(repo)[0] is None


def test_the_cli_prints_the_version_or_nothing(
    repo: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert REL.main(["--root", str(repo), "next"]) == 0
    assert capsys.readouterr().out == ""

    _commit(repo, "fix: one")
    assert REL.main(["--root", str(repo), "next"]) == 0
    assert capsys.readouterr().out == "0.1.0\n"


# --------------------------------------------------------------- changelog ---

CHANGELOG = """\
# Changelog

Intro.

## [Unreleased]

### Added

- A thing.

## [0.1.0] - 2026-01-01

- First.

[Unreleased]: https://github.com/guilyx/beehave/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/guilyx/beehave/releases/tag/v0.1.0
"""

DAY = dt.date(2026, 11, 12)


def test_the_unreleased_section_becomes_the_release() -> None:
    out = REL.release_changelog(CHANGELOG, "0.2.0", "v0.1.0", [], DAY)

    assert out == (
        "# Changelog\n\nIntro.\n\n"
        "## [Unreleased]\n\n"
        "## [0.2.0] - 2026-11-12\n\n### Added\n\n- A thing.\n\n"
        "## [0.1.0] - 2026-01-01\n\n- First.\n\n"
        "[Unreleased]: https://github.com/guilyx/beehave/compare/v0.2.0...HEAD\n"
        "[0.2.0]: https://github.com/guilyx/beehave/compare/v0.1.0...v0.2.0\n"
        "[0.1.0]: https://github.com/guilyx/beehave/releases/tag/v0.1.0\n"
    )


def test_an_empty_unreleased_section_is_written_from_the_commits() -> None:
    text = "# Changelog\n\n## [Unreleased]\n\n[Unreleased]: https://example.com\n"
    commits = [
        REL.parse_commit(m)
        for m in ("feat: diff two trees", "fix(cli): exit code", "feat!: new schema", "docs: x")
    ]

    out = REL.release_changelog(text, "0.1.0", None, commits, DAY)

    assert out == (
        "# Changelog\n\n## [Unreleased]\n\n## [0.1.0] - 2026-11-12\n\n"
        "### Breaking changes\n\n- New schema\n\n"
        "### Added\n\n- Diff two trees\n\n"
        "### Fixed\n\n- Exit code\n\n"
        "[Unreleased]: https://github.com/guilyx/beehave/compare/v0.1.0...HEAD\n"
        "[0.1.0]: https://github.com/guilyx/beehave/releases/tag/v0.1.0\n"
    )


def test_a_changelog_without_unreleased_is_refused() -> None:
    with pytest.raises(ValueError, match="Unreleased"):
        REL.release_changelog("# Changelog\n", "0.1.0", None, [], DAY)


def test_the_cli_rewrites_changelog_md(repo: Path) -> None:
    (repo / "CHANGELOG.md").write_text("# Changelog\n\n## [Unreleased]\n\n- A.\n")
    _commit(repo, "feat: a")

    assert REL.main(["--root", str(repo), "changelog", "0.1.0"]) == 0

    text = (repo / "CHANGELOG.md").read_text()
    assert "## [0.1.0] - " in text
    assert text.endswith("[0.1.0]: https://github.com/guilyx/beehave/releases/tag/v0.1.0\n")


def test_the_real_changelog_can_be_released() -> None:
    text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    out = REL.release_changelog(text, "0.1.0", None, [], DAY)

    assert "## [Unreleased]\n\n## [0.1.0] - 2026-11-12\n\n" in out
    assert out.count("## [Unreleased]") == 1
    assert "[Unreleased]: https://github.com/guilyx/beehave/compare/v0.1.0...HEAD\n" in out
