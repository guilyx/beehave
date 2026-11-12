"""Node identity: stable paths and runtime ids (FD1, FD2)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import beehave
from beehave.cli import main
from beehave.config import Config
from beehave.flatten import flatten
from beehave.ids import IdScheme, NodeRef, node_refs, runtime_ids
from beehave.model import NodeKind
from beehave.parsers import parse_string
from beehave.parsers.btcpp_v4 import parse_string as parse_v4
from beehave.render.json import node_ref
from beehave.walk import build_graph
from tests.conftest import EXAMPLES

if TYPE_CHECKING:
    from pathlib import Path

# BehaviorTree.CPP's own example, from its "Loggers and Observer" tutorial
# (btcpp_website 9cc7aad, docs/tutorial-basics/tutorial_10_observer.md).
OBSERVER_TUTORIAL = """
<root BTCPP_format="4">
  <BehaviorTree ID="MainTree">
    <Sequence>
     <Fallback>
       <AlwaysFailure name="failing_action"/>
       <SubTree ID="SubTreeA" name="mysub"/>
     </Fallback>
     <AlwaysSuccess name="last_action"/>
    </Sequence>
  </BehaviorTree>

  <BehaviorTree ID="SubTreeA">
    <Sequence>
      <AlwaysSuccess name="action_subA"/>
      <SubTree ID="SubTreeB" name="sub_nested"/>
      <SubTree ID="SubTreeB" />
    </Sequence>
  </BehaviorTree>

  <BehaviorTree ID="SubTreeB">
    <AlwaysSuccess name="action_subB"/>
  </BehaviorTree>
</root>
"""

# What the tutorial prints: "UID -> fullPath".
OBSERVER_UIDS = {
    1: "Sequence::1",
    2: "Fallback::2",
    3: "failing_action",
    4: "mysub",
    5: "mysub/Sequence::5",
    6: "mysub/action_subA",
    7: "mysub/sub_nested",
    8: "mysub/sub_nested/action_subB",
    9: "mysub/SubTreeB::9",
    10: "mysub/SubTreeB::9/action_subB",
    11: "last_action",
}

# BT.CPP v3: nested SubTreePlus, a classic SubTree, decorators and conditions.
NESTED_V3 = """
<root main_tree_to_execute="Mission">
  <BehaviorTree ID="Mission">
    <Sequence name="main">
      <IsReady/>
      <SubTreePlus ID="Transit" target="{goal}"/>
      <RetryUntilSuccessful num_attempts="2">
        <SubTreePlus ID="Transit" name="second_leg" target="{home}"/>
      </RetryUntilSuccessful>
      <SubTree ID="Report"/>
    </Sequence>
  </BehaviorTree>
  <BehaviorTree ID="Transit">
    <Fallback>
      <Sequence>
        <IsClear/>
        <MoveTo target="{target}"/>
      </Sequence>
      <SubTreePlus ID="Report"/>
    </Fallback>
  </BehaviorTree>
  <BehaviorTree ID="Report">
    <SendReport/>
  </BehaviorTree>
  <TreeNodesModel>
    <Condition ID="IsReady"/>
    <Condition ID="IsClear"/>
  </TreeNodesModel>
</root>
"""


def flat_v4(xml: str, tree: str | None = None) -> beehave.FlatTree:
    return flatten(parse_v4(xml), tree)


def test_uids_and_runtime_paths_match_btcpp_observer_tutorial() -> None:
    nodes = runtime_ids(flat_v4(OBSERVER_TUTORIAL, "MainTree"))

    assert {uid: node.ref.runtime_path for uid, node in nodes.items()} == OBSERVER_UIDS


def test_preorder_scheme_counts_from_zero_in_the_same_order() -> None:
    flat = flat_v4(OBSERVER_TUTORIAL, "MainTree")

    v4 = runtime_ids(flat, IdScheme.BTCPP_V4)
    preorder = runtime_ids(flat, IdScheme.PREORDER)

    assert list(preorder) == list(range(11))
    assert [n.ref for n in preorder.values()] == [n.ref for n in v4.values()]
    assert preorder[0].parent is None
    assert preorder[3].kind is NodeKind.SUBTREE
    assert preorder[3].subtree == "SubTreeA"
    # The subtree node comes right before the root of the tree it includes.
    assert preorder[4].parent == 3
    assert preorder[4].type == "Sequence"
    assert v4[5].parent == 4


def test_nested_subtree_plus_golden() -> None:
    flat = flatten(parse_string(NESTED_V3))

    nodes = runtime_ids(flat, IdScheme.PREORDER)

    assert [(n.id, n.parent, n.type, n.ref.path, n.ref.runtime_path) for n in nodes.values()] == [
        (0, None, "Sequence", "main", "main"),
        (1, 0, "IsReady", "main/IsReady", "IsReady::2"),
        (2, 0, "SubTreePlus", "main/Transit", "Transit::3"),
        (3, 2, "Fallback", "main/Transit/Fallback", "Transit::3/Fallback::4"),
        (4, 3, "Sequence", "main/Transit/Fallback/Sequence", "Transit::3/Sequence::5"),
        (5, 4, "IsClear", "main/Transit/Fallback/Sequence/IsClear", "Transit::3/IsClear::6"),
        (6, 4, "MoveTo", "main/Transit/Fallback/Sequence/MoveTo", "Transit::3/MoveTo::7"),
        (7, 3, "SubTreePlus", "main/Transit/Fallback/Report", "Transit::3/Report::8"),
        (
            8,
            7,
            "SendReport",
            "main/Transit/Fallback/Report/SendReport",
            "Transit::3/Report::8/SendReport::9",
        ),
        (9, 0, "RetryUntilSuccessful", "main/RetryUntilSuccessful", "RetryUntilSuccessful::10"),
        (10, 9, "SubTreePlus", "main/RetryUntilSuccessful/second_leg", "second_leg"),
        (
            11,
            10,
            "Fallback",
            "main/RetryUntilSuccessful/second_leg/Fallback",
            "second_leg/Fallback::12",
        ),
        (
            12,
            11,
            "Sequence",
            "main/RetryUntilSuccessful/second_leg/Fallback/Sequence",
            "second_leg/Sequence::13",
        ),
        (
            13,
            12,
            "IsClear",
            "main/RetryUntilSuccessful/second_leg/Fallback/Sequence/IsClear",
            "second_leg/IsClear::14",
        ),
        (
            14,
            12,
            "MoveTo",
            "main/RetryUntilSuccessful/second_leg/Fallback/Sequence/MoveTo",
            "second_leg/MoveTo::15",
        ),
        (
            15,
            11,
            "SubTreePlus",
            "main/RetryUntilSuccessful/second_leg/Fallback/Report",
            "second_leg/Report::16",
        ),
        (
            16,
            15,
            "SendReport",
            "main/RetryUntilSuccessful/second_leg/Fallback/Report/SendReport",
            "second_leg/Report::16/SendReport::17",
        ),
        (17, 0, "SubTree", "main/Report", "Report::18"),
        (18, 17, "SendReport", "main/Report/SendReport", "Report::18/SendReport::19"),
    ]


def test_actions_carry_their_node() -> None:
    graph = build_graph(flatten(parse_string(NESTED_V3)))

    refs = {v.label: v.node for v in reversed(graph.actions)}
    assert [v.node.uid for v in graph.actions if v.node] == [7, 9, 15, 17, 19]
    assert refs["SendReport"] == NodeRef(
        "main/Transit/Fallback/Report/SendReport", 9, "Transit::3/Report::8/SendReport::9"
    )
    assert all(v.node is None for v in graph.vertices if v.type is None)


def test_guard_conditions_carry_the_node_that_checks_them() -> None:
    graph = build_graph(flatten(parse_string(NESTED_V3)))

    first = graph.outgoing("start")[0]
    assert [(str(lit), lit.condition.node) for lit in first.guard] == [
        ("IsReady", NodeRef("main/IsReady", 2, "IsReady::2")),
        ("IsClear", NodeRef("main/Transit/Fallback/Sequence/IsClear", 6, "Transit::3/IsClear::6")),
    ]


def test_two_checks_of_one_condition_keep_their_own_nodes() -> None:
    # The second leg checks IsClear again: same condition key, another node.
    graph = build_graph(flatten(parse_string(NESTED_V3)))

    nodes = {
        lit.condition.node.path
        for edge in graph.edges
        for lit in edge.guard
        if lit.condition.node and lit.condition.label == "IsClear"
    }
    assert nodes == {
        "main/Transit/Fallback/Sequence/IsClear",
        "main/RetryUntilSuccessful/second_leg/Fallback/Sequence/IsClear",
    }


def test_scripts_switches_and_checks_belong_to_their_node() -> None:
    xml = """
    <root BTCPP_format="4" main_tree_to_execute="Main">
      <BehaviorTree ID="Main">
        <Sequence>
          <Switch2 variable="{mode}" case_1="fast" case_2="slow">
            <Act name="quick"/>
            <Act name="slow"/>
            <Act name="other"/>
          </Switch2>
          <Precondition if="battery &gt; 20" else="FAILURE">
            <Act name="go" _skipIf="paused"/>
          </Precondition>
        </Sequence>
      </BehaviorTree>
    </root>
    """
    graph = build_graph(flat_v4(xml))

    owners = {
        str(lit) if lit.positive else str(lit.negate()): lit.condition.node.path
        for edge in graph.edges
        for lit in edge.guard
        if lit.condition.node
    }
    assert owners == {
        "mode == fast": "Sequence/Switch2",
        "mode == slow": "Sequence/Switch2",
        "battery > 20": "Sequence/Precondition",
        "paused": "Sequence/Precondition/go",
    }


def test_unnamed_siblings_of_one_type_are_numbered() -> None:
    xml = (
        '<root><BehaviorTree ID="T"><Sequence>'
        '<Act/><Act/><Act name="x/y#z"/><Other/><Act/>'
        "</Sequence></BehaviorTree></root>"
    )

    refs = node_refs(flatten(parse_string(xml)))

    assert [ref.path for ref in refs.values()] == [
        "Sequence",
        "Sequence/Act",
        "Sequence/Act#2",
        "Sequence/x%2Fy%23z",
        "Sequence/Other",
        "Sequence/Act#3",
    ]


def test_a_path_survives_edits_elsewhere_in_the_tree() -> None:
    before = '<Sequence><A/><Fallback><B name="b"/><C/></Fallback></Sequence>'
    after = (
        "<Sequence><Z/><A/><Inverter><Y/></Inverter>"
        '<Fallback><C/><B name="b"/></Fallback></Sequence>'
    )

    def paths(body: str) -> dict[str, str]:
        graph = build_graph(
            flatten(parse_string(f'<root><BehaviorTree ID="T">{body}</BehaviorTree></root>'))
        )
        return {v.label: v.node.path for v in graph.actions if v.node}

    assert {k: v for k, v in paths(after).items() if k in "AbC"} == paths(before)


def test_a_node_named_like_its_type_gets_its_uid_in_the_runtime_path() -> None:
    xml = (
        '<root BTCPP_format="4"><BehaviorTree ID="T">'
        '<Sequence name="Sequence"><Act/></Sequence></BehaviorTree></root>'
    )

    refs = node_refs(flat_v4(xml))

    assert [ref.runtime_path for ref in refs.values()] == ["Sequence::1", "Act::2"]


def test_graph_finds_an_action_by_runtime_id_or_path() -> None:
    graph = build_graph(flat_v4(OBSERVER_TUTORIAL, "MainTree"))
    nested = build_graph(flatten(parse_string(NESTED_V3)))

    assert graph.vertex_for(1) is None  # AlwaysSuccess and friends are not actions
    move = nested.vertex_for(7)
    assert move is not None
    assert move.label == "MoveTo"
    assert nested.vertex_for(6, IdScheme.PREORDER) == move
    assert nested.vertex_at("main/Transit/Fallback/Sequence/MoveTo") == move
    assert nested.vertex_for(2) is None  # a condition
    assert nested.vertex_at("main") is None


def test_json_writes_no_tree_node_for_terminals() -> None:
    assert node_ref(None) is None


def test_ids_do_not_change_graph_equality() -> None:
    a = build_graph(flatten(parse_string(NESTED_V3)))
    b = build_graph(flatten(parse_string(NESTED_V3.replace('name="main"', 'name="renamed"'))))

    assert (a.vertices, a.edges) == (b.vertices, b.edges)
    assert a.actions[0].node != b.actions[0].node


def test_py_trees_paths_are_the_behaviour_names() -> None:
    py_trees = pytest.importorskip("py_trees")
    root = py_trees.composites.Sequence("Mission", memory=True)
    root.add_children([py_trees.behaviours.Success("Arm"), py_trees.behaviours.Success("Fly/Out")])

    result = beehave.analyze_py_trees(root, config=Config())
    refs = node_refs(result.tree)

    assert [(ref.path, ref.uid, ref.runtime_path) for ref in refs.values()] == [
        ("Mission", 1, None),
        ("Mission/Arm", 2, None),
        ("Mission/Fly%2FOut", 3, None),
    ]


# --------------------------------------------------------------------- CLI ---


@pytest.fixture
def observer_file(tmp_path: Path) -> str:
    path = tmp_path / "observer.xml"
    path.write_text(OBSERVER_TUTORIAL, encoding="utf-8")
    return str(path)


def test_cli_ids_prints_a_table(observer_file: str, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ids", observer_file, "-t", "MainTree", "-q"]) == 0

    lines = capsys.readouterr().out.splitlines()
    assert lines[0].split() == ["ID", "KIND", "VERTEX", "RUNTIME", "PATH", "PATH"]
    assert lines[5].split() == [
        "5",
        "control",
        "-",
        "mysub/Sequence::5",
        "Sequence/Fallback/mysub/Sequence",
    ]
    assert len(lines) == 12


def test_cli_ids_json_with_the_preorder_scheme(
    observer_file: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["ids", observer_file, "-t", "MainTree", "--scheme", "preorder", "--json"]) == 0

    data = json.loads(capsys.readouterr().out)
    assert data["schema"] == "beehave.runtime-ids"
    assert data["scheme"] == "preorder"
    node = data["nodes"][3]
    del node["location"]
    assert node == {
        "id": 3,
        "parent": 1,
        "kind": "subtree",
        "type": "SubTree",
        "name": "mysub",
        "subtree": "SubTreeA",
        "vertex": None,
        "path": "Sequence/Fallback/mysub",
        "uid": 4,
        "index": 3,
        "runtime_path": "mysub",
    }


def test_cli_ids_names_the_vertex_of_each_action(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["ids", str(EXAMPLES / "aerial" / "drone_mission.xml"), "--json", "-q"]) == 0

    data = json.loads(capsys.readouterr().out)
    vertices = {n["runtime_path"]: n["vertex"] for n in data["nodes"] if n["vertex"]}
    assert vertices["Arm::6"] == "a2"
    assert len(vertices) == len(
        beehave.analyze(EXAMPLES / "aerial" / "drone_mission.xml").graph.actions
    )
