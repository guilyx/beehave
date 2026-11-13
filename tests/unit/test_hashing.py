"""Content hashes of the action graph and of the inlined tree (FD3)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import TYPE_CHECKING

import pytest

import beehave
from beehave.cli import main
from beehave.config import Config
from beehave.flatten import flatten
from beehave.hashing import canonical_xml, graph_hash, tree_hash
from beehave.parsers import parse_string
from beehave.walk import build_graph
from tests.conftest import EXAMPLES, ROOT

if TYPE_CHECKING:
    from pathlib import Path

DRONE = EXAMPLES / "aerial" / "drone_mission.xml"
DRONE_V4 = EXAMPLES / "aerial" / "drone_mission_v4.xml"

# Pinned: a change to either canonical form must be deliberate (and versioned).
DRONE_GRAPH_HASH = "sha256:e3527ef932c22b8e4269b525f0b715993d09c8041ec7599ac4ec96936b9d192e"
DRONE_TREE_HASH = "sha256:a2a6aac5293fb84efadc5217879b2995bf29c8a1b2b9e33b0694a319d197d6dd"

TREE = """
<root main_tree_to_execute="Main">
  <BehaviorTree ID="Main">
    <Sequence name="mission">
      <IsReady/>
      <MoveTo target="{goal}" speed="2"/>
      <SubTreePlus ID="Report" channel="{radio}"/>
    </Sequence>
  </BehaviorTree>
  <BehaviorTree ID="Report">
    <Send to="{channel}"/>
  </BehaviorTree>
  <TreeNodesModel><Condition ID="IsReady"/></TreeNodesModel>
</root>
"""

# The same tree: other layout, attribute order, comments and quotes.
SAME_TREE = (
    "<root main_tree_to_execute='Main'><!-- a comment -->"
    '<BehaviorTree ID="Report"><Send   to="{channel}" /></BehaviorTree>'
    "<TreeNodesModel><Condition ID='IsReady'/></TreeNodesModel>"
    '<BehaviorTree ID="Main"><Sequence name="mission"><IsReady/>'
    '<MoveTo speed="2" target="{goal}"/>\n\n<SubTreePlus channel="{radio}" ID="Report"/>'
    "</Sequence></BehaviorTree></root>"
)


def hashes(xml: str, *, config: Config | None = None, tree: str | None = None) -> tuple[str, str]:
    flat = flatten(parse_string(xml, config=config), tree)
    return graph_hash(build_graph(flat)), tree_hash(flat)


def test_hashes_are_pinned_for_an_example() -> None:
    result = beehave.analyze(DRONE)

    assert graph_hash(result.graph) == DRONE_GRAPH_HASH
    assert tree_hash(result.tree) == DRONE_TREE_HASH
    assert result.graph.tree_hash == DRONE_TREE_HASH


def test_hashes_ignore_layout_attribute_order_and_comments() -> None:
    assert hashes(SAME_TREE) == hashes(TREE)


def test_hashes_ignore_where_the_tree_was_read_from(tmp_path: Path) -> None:
    (tmp_path / "a.xml").write_text(TREE, encoding="utf-8")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.xml").write_text(SAME_TREE, encoding="utf-8")

    a = beehave.analyze(tmp_path / "a.xml")
    b = beehave.analyze(tmp_path / "sub" / "b.xml")

    assert (graph_hash(a.graph), a.graph.tree_hash) == (graph_hash(b.graph), b.graph.tree_hash)


@pytest.mark.parametrize(
    ("old", "new"),
    [
        ('speed="2"', 'speed="3"'),  # a port value
        ('speed="2"', 'speed="2" mode="fast"'),  # a new port
        ('<Send to="{channel}"/>', '<Send to="{other}"/>'),  # a remapped key
        ("<IsReady/>", "<IsReady/><Beep/>"),  # a new action
    ],
)
def test_both_hashes_see_actions_and_ports(old: str, new: str) -> None:
    before, after = hashes(TREE), hashes(TREE.replace(old, new))

    assert before[0] != after[0]
    assert before[1] != after[1]


def test_the_tree_hash_sees_what_the_graph_hides() -> None:
    renamed = TREE.replace('name="mission"', 'name="sortie"')
    wrapped = TREE.replace("<IsReady/>", "<Inverter><Inverter><IsReady/></Inverter></Inverter>")

    for xml in (renamed, wrapped):
        graph_before, tree_before = hashes(TREE)
        graph_after, tree_after = hashes(xml)
        assert graph_after == graph_before
        assert tree_after != tree_before


def test_the_graph_hash_sees_the_config() -> None:
    as_action = Config(actions=frozenset({"IsReady"}))

    assert hashes(TREE)[0] != hashes(TREE, config=as_action)[0]
    assert hashes(TREE)[1] == hashes(TREE, config=as_action)[1]


def test_the_graph_hash_sees_the_structure() -> None:
    swapped = TREE.replace("<Sequence", "<Fallback").replace("</Sequence>", "</Fallback>")

    assert hashes(TREE)[0] != hashes(swapped)[0]


def test_v3_and_v4_versions_of_a_tree_have_the_same_graph_hash() -> None:
    v3, v4 = beehave.analyze(DRONE), beehave.analyze(DRONE_V4)

    assert graph_hash(v3.graph) == graph_hash(v4.graph)
    assert tree_hash(v3.tree) != tree_hash(v4.tree)  # the inlined XML differs


def test_canonical_xml_inlines_subtrees_and_sorts_attributes() -> None:
    flat = flatten(parse_string(SAME_TREE))

    assert canonical_xml(flat) == (
        '<root beehave_tree_hash="1" format="btcpp-v3"><BehaviorTree ID="Main">'
        '<Sequence name="mission"><IsReady/><MoveTo speed="2" target="{goal}"/>'
        '<SubTreePlus ID="Report" channel="{radio}"><Send to="{radio}"/></SubTreePlus>'
        "</Sequence></BehaviorTree></root>"
    )


def test_canonical_xml_escapes_values_and_keeps_whitespace_distinct() -> None:
    xml = (
        '<root><BehaviorTree ID="T"><Say text="a &amp; &quot;b&quot;&#10;c&#9;d"/>'
        "</BehaviorTree></root>"
    )

    assert '<Say text="a &amp; &quot;b&quot;&#10;c&#9;d"/>' in canonical_xml(
        flatten(parse_string(xml))
    )
    spaced = xml.replace("&#10;", " ").replace("&#9;", " ")
    assert hashes(xml)[1] != hashes(spaced)[1]


def test_py_trees_types_that_are_not_xml_names_are_written_as_attributes() -> None:
    py_trees = pytest.importorskip("py_trees")
    root = py_trees.composites.Sequence("Mission", memory=True)
    root.add_child(py_trees.behaviours.Success("Arm"))

    xml = canonical_xml(beehave.analyze_py_trees(root).tree)

    assert '<_ _type="Sequence(memory=True)" name="Mission"><Success name="Arm"/></_>' in xml


def test_hashes_do_not_depend_on_the_process() -> None:
    code = (
        "import beehave;"
        f"r = beehave.analyze({str(DRONE)!r});"
        "print(beehave.graph_hash(r.graph), beehave.tree_hash(r.tree))"
    )
    env = {**os.environ, "PYTHONHASHSEED": "12345", "PYTHONPATH": str(ROOT / "src")}

    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True, env=env
    ).stdout

    assert out.split() == [DRONE_GRAPH_HASH, DRONE_TREE_HASH]


# --------------------------------------------------------------- outputs ---


def test_json_carries_both_hashes() -> None:
    data = json.loads(beehave.to_json(beehave.analyze(DRONE).graph))

    assert data["graph_hash"] == DRONE_GRAPH_HASH
    assert data["tree_hash"] == DRONE_TREE_HASH


def test_cli_prints_the_hashes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", str(DRONE), "--print-hash", "-q"]) == 0

    assert capsys.readouterr().out == f"graph {DRONE_GRAPH_HASH}\ntree  {DRONE_TREE_HASH}\n"
