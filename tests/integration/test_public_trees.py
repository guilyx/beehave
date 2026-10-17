"""Beehave on real, public trees (BT.CPP examples, Groot test data, Nav2).

Every v3 tree must load, flatten and walk without errors. The text graph and
the stats of each tree are pinned as snapshots, so any change in behaviour shows
up as a reviewable diff. Every v4 tree must be refused with a clear message.

The fixtures are byte-identical upstream files; see tests/fixtures/public/README.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

import beehave
from beehave.errors import UnsupportedFormatError
from tests.conftest import FIXTURES

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

PUBLIC = FIXTURES / "public"
NAV2_MODELS = PUBLIC / "nav2" / "nav2_behavior_tree" / "nav2_tree_nodes.xml"

# (name, tree file); trees that are only included by others are covered through them.
V3_TREES = [
    ("btcpp-subtree-test", "btcpp-v3/examples/test_files/subtree_test.xml"),
    ("btcpp-nested-includes", "btcpp-v3/tests/trees/parent_include_child_include_parent.xml"),
    ("groot-crossdoor", "groot/test_data/crossdoor_with_subtree.xml"),
    ("groot-show-all", "groot/test_data/show_all.xml"),
    ("groot-subtree-remapping", "groot/test_data/subtree_with_remapping.xml"),
    ("groot-key-reordering", "groot/test_data/test_xml_key_reordering_issue.xml"),
    ("nav2-follow-point", "nav2/nav2_bt_navigator/behavior_trees/follow_point.xml"),
    (
        "nav2-replanning-recovery",
        "nav2/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml",
    ),
    (
        "nav2-goal-patience",
        (
            "nav2/nav2_bt_navigator/behavior_trees/"
            "navigate_to_pose_w_replanning_goal_patience_and_recovery.xml"
        ),
    ),
    (
        "nav2-replan-if-invalid",
        (
            "nav2/nav2_bt_navigator/behavior_trees/"
            "navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml"
        ),
    ),
    ("nav2-odometry-calibration", "nav2/nav2_bt_navigator/behavior_trees/odometry_calibration.xml"),
]

V4_TREES = [
    "v4/btcpp/examples/test_files/log_test.xml",
    "v4/btcpp/examples/test_files/Check.xml",  # no BTCPP_format marker
    "v4/nav2-jazzy/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml",
    (
        "v4/nav2-jazzy/nav2_bt_navigator/behavior_trees/"
        "navigate_to_pose_w_replanning_goal_patience_and_recovery.xml"
    ),
]


class _TextSnapshot(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "txt"


def _analyze(relative: str) -> beehave.Analysis:
    files = [Path(relative)]
    if relative.startswith("nav2/"):
        # Nav2 declares its conditions in a separate models file.
        files.append(NAV2_MODELS.relative_to(PUBLIC))
    return beehave.analyze(*files)


@pytest.fixture(autouse=True)
def _in_public_dir(monkeypatch: pytest.MonkeyPatch) -> None:
    # Relative paths keep snapshot locations independent of the checkout.
    monkeypatch.chdir(PUBLIC)


@pytest.mark.parametrize(("name", "relative"), V3_TREES, ids=[n for n, _ in V3_TREES])
def test_v3_tree_graph(name: str, relative: str, snapshot: SnapshotAssertion) -> None:
    result = _analyze(relative)

    diagnostics = "".join(f"{d}\n" for d in result.graph.diagnostics)
    report = f"{beehave.to_text(result.graph)}\n{result.stats.to_text()}\n{diagnostics}"
    assert report == snapshot(extension_class=_TextSnapshot)


@pytest.mark.parametrize(("name", "relative"), V3_TREES, ids=[n for n, _ in V3_TREES])
def test_v3_tree_renders_in_every_format(name: str, relative: str) -> None:
    graph = _analyze(relative).graph

    for render in (beehave.to_mermaid, beehave.to_dot, beehave.to_json):
        assert render(graph)


def test_nav2_conditions_come_from_the_models_file() -> None:
    result = _analyze(V3_TREES[7][1])

    guards = {str(lit) for e in result.graph.edges for lit in e.guard}
    assert "GoalUpdated" in guards


def test_same_subtree_used_twice_gives_two_copies() -> None:
    result = _analyze("groot/test_data/subtree_with_remapping.xml")

    subtree_actions = [v for v in result.graph.actions if v.subtrees]
    assert len(subtree_actions) == 2
    assert subtree_actions[0].id != subtree_actions[1].id


@pytest.mark.parametrize("relative", V4_TREES)
def test_v4_trees_are_refused(relative: str) -> None:
    with pytest.raises(UnsupportedFormatError, match=r"BT\.CPP v4"):
        beehave.analyze(relative)
