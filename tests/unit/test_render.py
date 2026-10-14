"""Renderers: text, Mermaid, Graphviz DOT and JSON."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

import pytest
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

from beehave.flatten import flatten
from beehave.parsers import parse_file, parse_string
from beehave.render import to_dot, to_json, to_mermaid, to_text
from beehave.walk import build_graph
from tests.conftest import EXAMPLES, tree_xml

if TYPE_CHECKING:
    from syrupy.assertion import SnapshotAssertion

    from beehave.graph import ActionGraph


class _TextSnapshot(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "txt"


class _MermaidSnapshot(_TextSnapshot):
    file_extension = "mmd"


class _DotSnapshot(_TextSnapshot):
    file_extension = "dot"


class _JsonSnapshot(_TextSnapshot):
    file_extension = "json"


def _graph(body: str, extra: str = "") -> ActionGraph:
    return build_graph(flatten(parse_string(tree_xml(body, extra=extra), source="t.xml")))


@pytest.fixture
def drone(monkeypatch: pytest.MonkeyPatch) -> ActionGraph:
    # Relative path, so locations in snapshots do not depend on the checkout.
    monkeypatch.chdir(EXAMPLES / "aerial")
    return build_graph(flatten(parse_file("drone_mission.xml")))


# ------------------------------------------------------------------ text ---


def test_text_reads_like_the_design_doc() -> None:
    g = _graph(
        "<Sequence><A/><Fallback><Sequence><C/><B/></Sequence><X/></Fallback></Sequence>",
        extra='<TreeNodesModel><Condition ID="C"/></TreeNodesModel>',
    )

    assert to_text(g) == (
        "START --> A\n"
        "A --[success and C]--> B\n"
        "A --[success and not C]--> X\n"
        "A --[failure]--> FAILURE\n"
        "B --[success]--> SUCCESS\n"
        "B --[failure]--> X\n"
        "X --[success]--> SUCCESS\n"
        "X --[failure]--> FAILURE\n"
    )


def test_text_disambiguates_actions_with_the_same_label() -> None:
    text = to_text(_graph("<Sequence><Fly/><Fly/></Sequence>"))

    assert "START --> Fly#1\n" in text
    assert "Fly#1 --[success]--> Fly#2\n" in text


def test_text_lists_notes_after_the_edges() -> None:
    text = to_text(_graph('<RetryUntilSuccessful num_attempts="3"><A/></RetryUntilSuccessful>'))

    assert text.endswith("\nnotes:\n  A: retry ×3\n")


def test_text_snapshot(drone: ActionGraph, snapshot: SnapshotAssertion) -> None:
    assert to_text(drone) == snapshot(extension_class=_TextSnapshot)


# --------------------------------------------------------------- mermaid ---


def test_mermaid_is_a_top_down_flowchart() -> None:
    lines = to_mermaid(_graph("<A/>")).splitlines()

    assert "flowchart TD" in lines
    assert '    a1["A"]' in lines
    assert "    start --> a1" in lines
    assert '    a1 -->|"success"| success' in lines


def test_mermaid_draws_failure_edges_dashed() -> None:
    assert '    a1 -.->|"failure"| failure' in to_mermaid(_graph("<A/>")).splitlines()


def test_mermaid_escapes_labels() -> None:
    out = to_mermaid(_graph('<Action ID="A" name="say &quot;hi&quot; &lt;now&gt; #1"/>'))

    assert 'a1["say #quot;hi#quot; #lt;now#gt; #35;1"]' in out


def test_mermaid_snapshot(drone: ActionGraph, snapshot: SnapshotAssertion) -> None:
    assert to_mermaid(drone) == snapshot(extension_class=_MermaidSnapshot)


# ------------------------------------------------------------------- dot ---


def test_dot_is_a_digraph_named_after_the_tree() -> None:
    out = to_dot(_graph("<A/>"))

    assert 'digraph "Main" {' in out.splitlines()
    assert '  "start" -> "a1" [color="#1b1813"];' in out
    assert '  "a1" -> "failure" [label="failure"' in out


def test_dot_escapes_labels() -> None:
    out = to_dot(_graph('<Action ID="A" name="a &quot;b&quot; c\\d"/>'))

    assert '"a1" [label="a \\"b\\" c\\\\d"' in out


def test_dot_snapshot(drone: ActionGraph, snapshot: SnapshotAssertion) -> None:
    assert to_dot(drone) == snapshot(extension_class=_DotSnapshot)


# ------------------------------------------------------------------ json ---


def test_json_document_shape() -> None:
    data: dict[str, Any] = json.loads(
        to_json(_graph('<Sequence><C/><Fly zone="3"/></Sequence>', extra=_COND))
    )

    assert data["schema"] == "beehave.action-graph"
    assert data["version"] == 1
    assert data["tree"] == "Main"
    assert data["source_format"] == "btcpp-v3"
    assert data["nodes"][1] == {
        "id": "a1",
        "kind": "action",
        "label": "Fly",
        "type": "Fly",
        "ports": {"zone": "3"},
        "notes": [],
        "subtrees": [],
        "location": {"file": "t.xml", "line": 1},
    }
    assert data["edges"][0] == {
        "from": "start",
        "to": "a1",
        "outcome": None,
        "guard": [{"condition": "C", "key": "C()", "holds": True}],
    }


def test_json_includes_diagnostics() -> None:
    data = json.loads(to_json(_graph("<Parallel><A/><B/></Parallel>")))

    assert data["diagnostics"][0]["code"] == "approximated"
    assert data["diagnostics"][0]["node_type"] == "Parallel"
    assert data["diagnostics"][0]["severity"] == "warning"


def test_json_snapshot(drone: ActionGraph, snapshot: SnapshotAssertion) -> None:
    assert to_json(drone) == snapshot(extension_class=_JsonSnapshot)


_COND = '<TreeNodesModel><Condition ID="C"/></TreeNodesModel>'


# ----------------------------------------------------------------- theme ---


def test_mermaid_colours_edges_by_outcome() -> None:
    lines = to_mermaid(_graph("<Sequence><A/><B/></Sequence>")).splitlines()

    assert "    linkStyle 0 stroke:#1b1813,stroke-width:1.75px" in lines
    assert "    linkStyle 1,3 stroke:#107550,stroke-width:1.75px" in lines
    assert "    linkStyle 2,4 stroke:#b93917,stroke-width:1.75px,stroke-dasharray:7 4" in lines


def test_dot_colours_edges_by_outcome_and_keeps_dashes_for_failure() -> None:
    out = to_dot(_graph("<A/>"))

    assert '"a1" -> "success" [label="success", color="#107550"' in out
    assert '"a1" -> "failure" [label="failure", color="#b93917", style=dashed' in out


def test_mermaid_output_carries_its_theme() -> None:
    out = to_mermaid(_graph("<A/>"))

    assert out.startswith("---\nconfig:\n")
    assert '    edgeLabelBackground: "#f5f0e9"' in out.splitlines()
