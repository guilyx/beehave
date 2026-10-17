"""Pilot metrics (size, reduction, breakage) and the high-level API."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

import beehave
from beehave.config import Config
from tests.conftest import EXAMPLES

if TYPE_CHECKING:
    from pathlib import Path

DRONE = EXAMPLES / "aerial" / "drone_mission.xml"


def test_analyze_runs_the_whole_pipeline() -> None:
    result = beehave.analyze(DRONE)

    assert result.tree.id == "DroneMission"
    assert len(result.graph.actions) == 10
    assert "ReturnToLaunch" in result.document.trees


def test_stats_on_the_drone_mission() -> None:
    stats = beehave.analyze(DRONE).stats

    assert stats.tree == "DroneMission"
    assert stats.nodes == 22
    assert stats.nodes_by_kind == {
        "control": 7,
        "decorator": 2,
        "condition": 2,
        "action": 10,
        "subtree": 1,
    }
    assert stats.actions == 10
    assert stats.transitions == 23
    assert stats.reduction == pytest.approx(1 - 10 / 22)
    assert stats.longest_guard == 1  # "success and IsBatteryOK": the outcome is not a term
    assert stats.approximated == {
        "ReactiveFallback": 1,
        "ReactiveSequence": 1,
        "RetryUntilSuccessful": 1,
    }


def test_stats_as_text_and_dict() -> None:
    stats = beehave.analyze(DRONE).stats

    text = stats.to_text()
    assert "nodes          22" in text
    assert "reduction      55% (22 nodes -> 10 actions)" in text
    assert (
        "approximated   ReactiveFallback ×1, ReactiveSequence ×1, RetryUntilSuccessful ×1" in text
    )
    assert stats.to_dict()["reduction"] == pytest.approx(1 - 10 / 22)


def test_stats_without_approximations_say_so(tmp_path: Path) -> None:
    tree = tmp_path / "t.xml"
    tree.write_text(
        '<root><BehaviorTree ID="T"><Sequence><A/><B/></Sequence></BehaviorTree></root>'
    )

    assert "approximated   none" in beehave.analyze(tree).stats.to_text()


def test_analyze_merges_load_diagnostics_into_the_graph(tmp_path: Path) -> None:
    tree = tmp_path / "t.xml"
    tree.write_text(
        '<root><include ros_pkg="p" path="x.xml"/><BehaviorTree ID="T"><A/></BehaviorTree></root>'
    )

    codes = [d.code for d in beehave.analyze(tree).graph.diagnostics]
    assert codes == ["unresolved-include"]


def test_analyze_accepts_config_and_tree(tmp_path: Path) -> None:
    tree = tmp_path / "t.xml"
    tree.write_text(
        '<root><BehaviorTree ID="A"><X/></BehaviorTree>'
        '<BehaviorTree ID="B"><Sequence><Ok/><Y/></Sequence></BehaviorTree></root>'
    )

    result = beehave.analyze(tree, tree="B", config=Config(conditions=frozenset({"Ok"})))

    assert [v.label for v in result.graph.actions] == ["Y"]


def test_public_api_surface() -> None:
    for name in (
        "analyze",
        "analyze_py_trees",
        "from_py_trees",
        "load_py_trees",
        "Analysis",
        "Config",
        "load_config",
        "parse_file",
        "parse_string",
        "flatten",
        "build_graph",
        "to_text",
        "to_mermaid",
        "to_dot",
        "to_json",
        "BeehaveError",
        "__version__",
    ):
        assert hasattr(beehave, name), name
