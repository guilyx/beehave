"""The ``beehave`` command line."""

from __future__ import annotations

import json
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

from beehave import __version__
from beehave.cli import main
from tests.conftest import EXAMPLES

if TYPE_CHECKING:
    from pathlib import Path

DRONE = str(EXAMPLES / "aerial" / "drone_mission.xml")


def test_graph_defaults_to_text(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", DRONE, "--quiet"]) == 0

    out = capsys.readouterr().out
    assert out.startswith("START --[IsBatteryCritical]--> LandNow\n")


@pytest.mark.parametrize(
    ("fmt", "marker"),
    [("mermaid", "flowchart TD"), ("dot", 'digraph "DroneMission" {'), ("json", '"schema"')],
)
def test_graph_formats(fmt: str, marker: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", DRONE, "-f", fmt, "-q"]) == 0

    assert marker in capsys.readouterr().out


def test_graph_writes_to_a_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "g.mmd"

    assert main(["graph", DRONE, "-f", "mermaid", "-o", str(out), "-q"]) == 0

    assert "%% Beehave action graph" in out.read_text(encoding="utf-8")
    assert capsys.readouterr().out == ""


def test_diagnostics_go_to_stderr(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", DRONE]) == 0

    err = capsys.readouterr().err
    assert 'warning: ReactiveFallback "mission_with_failsafe": walked like a Fallback' in err
    assert "[approximated]" in err


def test_quiet_hides_diagnostics(capsys: pytest.CaptureFixture[str]) -> None:
    main(["graph", DRONE, "-q"])

    assert capsys.readouterr().err == ""


def test_stats(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats", DRONE, "-q"]) == 0

    assert "reduction      55%" in capsys.readouterr().out


def test_stats_json(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats", DRONE, "--json", "-q"]) == 0

    assert json.loads(capsys.readouterr().out)["actions"] == 10


def test_trees_lists_every_tree_and_marks_the_main_one(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(["trees", DRONE]) == 0

    assert capsys.readouterr().out == "DroneMission (main)\nReturnToLaunch\n"


def test_tree_option_selects_a_tree(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", DRONE, "-t", "ReturnToLaunch", "-q"]) == 0

    assert capsys.readouterr().out.startswith("START --> FlyHome\n")


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
        (
            (
                "<root><BehaviorTree ID='T'><Sequence memory='true'><A/></Sequence>"
                "</BehaviorTree></root>"
            ),
            "looks like py_trees XML",
        ),
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

    assert main(["graph", DRONE, "-c", str(config)]) == 1

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
        [sys.executable, "-m", "beehave", "trees", DRONE],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.startswith("DroneMission (main)")


def test_graph_reads_bt_cpp_v4(capsys: pytest.CaptureFixture[str]) -> None:
    drone_v4 = str(EXAMPLES / "aerial" / "drone_mission_v4.xml")

    assert main(["graph", drone_v4, "-q"]) == 0

    assert capsys.readouterr().out.startswith("START --[IsBatteryCritical]--> LandNow\n")
