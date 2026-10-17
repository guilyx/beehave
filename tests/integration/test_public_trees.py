"""Beehave on real, public trees (BT.CPP examples, Groot test data, Nav2…).

Every v3 and v4 tree must load, flatten and walk without errors. The text graph
and the stats of each tree are pinned as snapshots, so any change in behaviour
shows up as a reviewable diff. Trees that exist in both versions must give the
same graph, and the files BT.CPP itself rejects must be rejected.

The fixtures are byte-identical upstream files; see tests/fixtures/public/README.md.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

import beehave
from beehave.errors import BeehaveError
from tests.conftest import FIXTURES

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

PUBLIC = FIXTURES / "public"
NAV2_MODELS = PUBLIC / "nav2" / "nav2_behavior_tree" / "nav2_tree_nodes.xml"
NAV2_JAZZY_MODELS = "v4/nav2-jazzy/nav2_behavior_tree/nav2_tree_nodes.xml"

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

_JAZZY = "v4/nav2-jazzy/nav2_bt_navigator/behavior_trees/"
_LITEBT = "v4/litebt/tests/LiteBT.Tests/DifferentialCorpus/"
_ORACLE = "v4/litebt/tools/btcpp-oracle/samples/"

# (name, files, tree); files are relative to the public fixtures folder.
V4_TREES: list[tuple[str, tuple[str, ...], str | None]] = [
    ("btcpp-check", ("v4/btcpp/examples/test_files/Check.xml",), None),
    ("btcpp-log-test", ("v4/btcpp/examples/test_files/log_test.xml",), "Main"),
    ("btcpp-subtree-test", ("v4/btcpp/examples/test_files/subtree_test.xml",), None),
    ("btcpp-talk", ("v4/btcpp/examples/test_files/subtrees/Talk.xml",), None),
    ("btcpp-corpus1", ("v4/btcpp/fuzzing/corpus/bt_corpus/corpus1.xml",), None),
    (
        "btcpp-nested-includes",
        ("v4/btcpp/tests/trees/parent_include_child_include_parent.xml",),
        None,
    ),
    (
        "btcpp-ros2-door-closed",
        ("v4/btcpp-ros2/btcpp_ros2_samples/behavior_trees/door_closed.xml",),
        None,
    ),
    (
        "btcpp-ros2-cross-door",
        (
            "v4/btcpp-ros2/btcpp_ros2_samples/behavior_trees/cross_door.xml",
            "v4/btcpp-ros2/btcpp_ros2_samples/behavior_trees/door_closed.xml",
        ),
        "CrossDoor",
    ),
    (
        "btcpp-ros2-sleep",
        ("v4/btcpp-ros2/btcpp_ros2_samples/behavior_trees/sleep_action.xml",),
        None,
    ),
    ("auto-apms-demo", ("v4/auto-apms/auto_apms_examples/behavior/demo.xml",), "HelloWorld"),
    (
        "auto-apms-skill-tree",
        ("v4/auto-apms/auto_apms_examples/behavior/simple_skill_tree.xml",),
        None,
    ),
    (
        "auto-apms-orchestrator",
        ("v4/auto-apms/auto_apms_mission/config/orchestrator_base.xml",),
        None,
    ),
    *(
        (f"litebt-{name}", (f"{_LITEBT}{name}.xml",), None)
        for name in (
            "a1-sequence",
            "a2-reactive",
            "a3-parallel",
            "a4-branch",
            "a5-decorator",
            "a6-script",
            "a7-precond-order",
            "b1-repeat",
            "b2-retry",
            "b3-subtree",
            "b4-runonce",
            "b5-subtree-local",
            "b6-halt",
            "b10-async-fallback",
            "b11-subtree-forward",
            "f1-ifthenelse-stale",
            "f2-whiledoelse-strand",
            "f3-entry-updated",
        )
    ),
    ("litebt-oracle-tier-a", (f"{_ORACLE}tier-a.xml",), None),
    ("litebt-oracle-tier-a-controls", (f"{_ORACLE}tier-a-controls.xml",), None),
    *(
        (f"nav2-jazzy-{name}", (f"{_JAZZY}{file}.xml", NAV2_JAZZY_MODELS), None)
        for name, file in (
            ("follow-point", "follow_point"),
            ("replanning-recovery", "navigate_to_pose_w_replanning_and_recovery"),
            ("goal-patience", "navigate_to_pose_w_replanning_goal_patience_and_recovery"),
            ("through-poses", "navigate_through_poses_w_replanning_and_recovery"),
            (
                "consistent-replanning",
                "nav_to_pose_with_consistent_replanning_and_if_path_becomes_invalid",
            ),
            ("odometry-calibration", "odometry_calibration"),
        )
    ),
    ("scan-n-plan", ("v4/scan-n-plan/snp_application/config/snp.xml",), "main"),
]

# v4 files paired with their v3 version, which must give the same graph.
V3_V4_PAIRS = [
    ("btcpp-v3/examples/test_files/Check.xml", "v4/btcpp/examples/test_files/Check.xml"),
    (
        "btcpp-v3/examples/test_files/subtrees/Talk.xml",
        "v4/btcpp/examples/test_files/subtrees/Talk.xml",
    ),
    (
        "btcpp-v3/examples/test_files/subtree_test.xml",
        "v4/btcpp/examples/test_files/subtree_test.xml",
    ),
    *(
        (f"btcpp-v3/tests/trees/{name}", f"v4/btcpp/tests/trees/{name}")
        for name in (
            "parent_include_child_include_parent.xml",
            "child/child_include_parent.xml",
            "parent_no_include.xml",
        )
    ),
]

# Files BT.CPP itself refuses to load.
INVALID_V4 = [
    ("v4/btcpp/fuzzing/corpus/bt_corpus/corpus3.xml", "subtree 'SubTree' is not defined"),
    ("v4/btcpp/fuzzing/corpus/bt_corpus/corpus4.xml", r"<ForceSuccess> needs exactly 1 child"),
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


@pytest.mark.parametrize(("name", "files", "tree"), V4_TREES, ids=[n for n, _, _ in V4_TREES])
def test_v4_tree_graph(
    name: str, files: tuple[str, ...], tree: str | None, snapshot: SnapshotAssertion
) -> None:
    result = beehave.analyze(*files, tree=tree)

    assert result.graph.format == "btcpp-v4"
    diagnostics = "".join(f"{d}\n" for d in result.graph.diagnostics)
    report = f"{beehave.to_text(result.graph)}\n{result.stats.to_text()}\n{diagnostics}"
    assert report == snapshot(extension_class=_TextSnapshot)


@pytest.mark.parametrize(("name", "files", "tree"), V4_TREES, ids=[n for n, _, _ in V4_TREES])
def test_v4_tree_renders_in_every_format(
    name: str, files: tuple[str, ...], tree: str | None
) -> None:
    graph = beehave.analyze(*files, tree=tree).graph

    for render in (beehave.to_mermaid, beehave.to_dot, beehave.to_json):
        assert render(graph)


@pytest.mark.parametrize(("v3", "v4"), V3_V4_PAIRS, ids=[Path(v).stem for _, v in V3_V4_PAIRS])
def test_v3_and_v4_versions_give_the_same_graph(v3: str, v4: str) -> None:
    graph_v3, graph_v4 = beehave.analyze(v3).graph, beehave.analyze(v4).graph

    assert (graph_v3.format, graph_v4.format) == ("btcpp-v3", "btcpp-v4")
    assert beehave.to_text(graph_v4) == beehave.to_text(graph_v3)


@pytest.mark.parametrize(
    ("relative", "message"), INVALID_V4, ids=[Path(r).stem for r, _ in INVALID_V4]
)
def test_files_bt_cpp_rejects_are_rejected(relative: str, message: str) -> None:
    with pytest.raises(BeehaveError, match=message):
        beehave.analyze(relative)


def test_a_marker_less_v4_file_is_read_as_v4() -> None:
    # Check.xml has no BTCPP_format; SequenceWithMemory gives it away.
    assert beehave.analyze("v4/btcpp/examples/test_files/Check.xml").graph.format == "btcpp-v4"


def test_nav2_humble_and_jazzy_odometry_calibration_give_the_same_graph() -> None:
    # The only Nav2 tree that is the same in Humble (v3) and Jazzy (v4); the
    # others gained selector actions and recovery guards in Jazzy.
    humble = beehave.analyze(
        "nav2/nav2_bt_navigator/behavior_trees/odometry_calibration.xml",
        NAV2_MODELS.relative_to(PUBLIC),
    )
    jazzy = beehave.analyze(f"{_JAZZY}odometry_calibration.xml", NAV2_JAZZY_MODELS)

    assert beehave.to_text(jazzy.graph) == beehave.to_text(humble.graph)
