"""The ``beehave`` command line."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from beehave import __version__
from beehave.cli import main
from tests.conftest import FIXTURES

if TYPE_CHECKING:
    from pathlib import Path

LANDING = str(FIXTURES / "trees" / "landing.xml")


def test_graph_defaults_to_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", LANDING, "--quiet"]) == 0

    out = capsys.readouterr().out
    assert out.startswith("START --[Emergency]--> EmergencyLand\n")


@pytest.mark.parametrize(
    ("fmt", "marker"),
    [("mermaid", "flowchart TD"), ("dot", 'digraph "Mission" {'), ("json", '"schema"')],
)
def test_graph_formats(fmt: str, marker: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", LANDING, "-f", fmt, "-q"]) == 0

    assert marker in capsys.readouterr().out


def test_graph_writes_to_a_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "g.mmd"

    assert main(["graph", LANDING, "-f", "mermaid", "-o", str(out), "-q"]) == 0

    assert out.read_text(encoding="utf-8").startswith("%% Beehave action graph")
    assert capsys.readouterr().out == ""


def test_diagnostics_go_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", LANDING]) == 0

    err = capsys.readouterr().err
    assert "warning: ReactiveFallback: walked like a Fallback" in err
    assert "[approximated]" in err


def test_quiet_hides_diagnostics(capsys: pytest.CaptureFixture[str]) -> None:
    main(["graph", LANDING, "-q"])

    assert capsys.readouterr().err == ""


def test_stats(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats", LANDING, "-q"]) == 0

    assert "reduction      60%" in capsys.readouterr().out


def test_stats_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats", LANDING, "--json", "-q"]) == 0

    assert json.loads(capsys.readouterr().out)["actions"] == 8


def test_trees_lists_every_tree_and_marks_the_main_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["trees", LANDING]) == 0

    assert capsys.readouterr().out == "Mission (main)\nReturnHome\n"


def test_tree_option_selects_a_tree(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", LANDING, "-t", "ReturnHome", "-q"]) == 0

    assert capsys.readouterr().out.startswith("START --> ResolveHome\n")


def test_config_file_is_used(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    tree = tmp_path / "t.xml"
    tree.write_text(
        '<root><BehaviorTree ID="T"><Sequence><Ok/><Go/></Sequence></BehaviorTree></root>'
    )
    config = tmp_path / "beehave.yaml"
    config.write_text("conditions: [Ok]\n")

    assert main(["graph", str(tree), "-c", str(config)]) == 0

    assert capsys.readouterr().out.startswith("START --[Ok]--> Go\n")


def test_config_in_the_working_directory_is_found(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    (tmp_path / "t.xml").write_text(
        '<root><BehaviorTree ID="T"><Sequence><Ok/><Go/></Sequence></BehaviorTree></root>'
    )
    (tmp_path / "beehave.yaml").write_text("conditions: [Ok]\n")
    monkeypatch.chdir(tmp_path)

    assert main(["graph", "t.xml"]) == 0

    assert capsys.readouterr().out.startswith("START --[Ok]--> Go\n")


@pytest.mark.parametrize(
    ("xml", "message"),
    [
        ('<root BTCPP_format="4"><BehaviorTree ID="T"><A/></BehaviorTree></root>', "BT.CPP v4"),
        ("<root><BehaviorTree ID='T'><SubTree ID='Nope'/></BehaviorTree></root>", "'Nope'"),
        ("<root><BehaviorTree ID='T'><A></root>", "not well-formed"),
    ],
)
def test_bad_input_exits_with_one(
    xml: str, message: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tree = tmp_path / "t.xml"
    tree.write_text(xml)

    assert main(["graph", str(tree)]) == 1

    err = capsys.readouterr().err
    assert err.startswith("beehave: error: ")
    assert message in err


def test_missing_file_exits_with_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", str(tmp_path / "nope.xml")]) == 1

    assert "cannot read" in capsys.readouterr().err


def test_bad_config_exits_with_one(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    config = tmp_path / "c.yaml"
    config.write_text("conditions: 3\n")

    assert main(["graph", LANDING, "-c", str(config)]) == 1

    assert "must be a list" in capsys.readouterr().err


def test_usage_errors_exit_with_two() -> None:
    with pytest.raises(SystemExit) as info:
        main(["graph"])
    assert info.value.code == 2


def test_version(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_module_entry_point() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "beehave", "trees", LANDING],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("Mission (main)")
