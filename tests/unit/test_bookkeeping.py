"""Bookkeeping actions: left out of the graph, with their edges joined up (FD7).

Edges are written ``source -outcome-> target [guard]``, as in test_walk.py.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest

from beehave.config import Bookkeeping, Config, config_from_dict, load_config
from beehave.errors import ConfigError, ParseError
from beehave.flatten import flatten
from beehave.graph import ActionGraph, Outcome
from beehave.ids import runtime_ids
from beehave.model import NodeKind, Semantics
from beehave.parsers import parse_string
from beehave.walk import build_graph

if TYPE_CHECKING:
    from pathlib import Path

BOOKKEEPING = {"Log": {}, "Note": {"never_fails": True}}


def graph(body: str, *, v4: bool = False, **extra: Any) -> ActionGraph:
    config = config_from_dict({"conditions": ["C", "D"], "bookkeeping": BOOKKEEPING, **extra})
    marker = ' BTCPP_format="4"' if v4 else ""
    xml = f'<root{marker}><BehaviorTree ID="T">{body}</BehaviorTree></root>'
    document = parse_string(xml, config=config)
    g = build_graph(flatten(document))
    return replace(g, diagnostics=document.diagnostics + g.diagnostics)


def edges(g: ActionGraph) -> list[str]:
    out = []
    for e in g.edges:
        src, dst = g.vertex(e.source).label, g.vertex(e.target).label
        arrow = f"-{e.outcome.value}->" if e.outcome else "->"
        guard = f" [{' and '.join(map(str, e.guard))}]" if e.guard else ""
        out.append(f"{src} {arrow} {dst}{guard}")
    return out


# ------------------------------------------------------------------ config ---


def test_config_takes_a_list_or_a_mapping(tmp_path: Path) -> None:
    listed = tmp_path / "a.yaml"
    listed.write_text("bookkeeping: [LogMessage, SaveState]\n", encoding="utf-8")
    mapped = tmp_path / "b.yaml"
    mapped.write_text(
        "bookkeeping:\n  LogMessage:\n  SetFlag: {never_fails: true}\n", encoding="utf-8"
    )

    assert load_config(listed).bookkeeping == {
        "LogMessage": Bookkeeping(),
        "SaveState": Bookkeeping(),
    }
    assert load_config(mapped).bookkeeping == {
        "LogMessage": Bookkeeping(),
        "SetFlag": Bookkeeping(never_fails=True),
    }
    assert load_config(mapped).declared == {"LogMessage", "SetFlag"}


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ({"bookkeeping": "Log"}, "must be a list of node names, or map"),
        ({"bookkeeping": [1]}, "must be a list of node names, or map"),
        ({"bookkeeping": {"Log": {"never_fails": "yes"}}}, "must be a list"),
        ({"bookkeeping": {"Log": {"quiet": True}}}, "must be a list"),
        ({"bookkeeping": {"Log": []}}, "must be a list"),
        ({"bookkeeping": ["A"], "actions": ["A"]}, "under bookkeeping and as another kind"),
        ({"bookkeeping": ["A"], "nodes": {"A": "sequence"}}, "under bookkeeping and as another"),
    ],
)
def test_invalid_bookkeeping_is_refused(data: object, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        config_from_dict(data)


# ---------------------------------------------------------------- parsing ---


def test_a_bookkeeping_node_is_an_action_with_its_own_semantics() -> None:
    config = Config(bookkeeping={"Log": Bookkeeping(never_fails=True)})
    xml = '<root><BehaviorTree ID="T"><Log text="hi"/></BehaviorTree></root>'

    node = parse_string(xml, config=config).trees["T"].root

    assert (node.kind, node.semantics, node.options) == (
        NodeKind.ACTION,
        Semantics.BOOKKEEPING,
        {"never_fails": "true"},
    )


def test_a_bookkeeping_node_cannot_have_children() -> None:
    with pytest.raises(ParseError, match="<Log> cannot have children"):
        graph("<Log><A/></Log>")


def test_a_built_in_listed_as_bookkeeping_is_ignored_with_a_warning() -> None:
    g = graph("<Sequence><A/><Delay><B/></Delay></Sequence>", bookkeeping=["Delay"])

    assert [d.code for d in g.diagnostics] == ["bookkeeping-ignored"]


# ------------------------------------------------------------------- walk ---


def test_an_action_that_never_fails_is_skipped_over() -> None:
    assert edges(graph("<Sequence><A/><Note/><B/></Sequence>")) == [
        "START -> A",
        "A -success-> B",
        "A -failure-> FAILURE",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_an_action_that_may_fail_becomes_a_guard() -> None:
    assert edges(graph("<Sequence><A/><Log/><B/></Sequence>")) == [
        "START -> A",
        "A -success-> B [Log succeeded]",
        "A -success-> FAILURE [Log failed]",
        "A -failure-> FAILURE",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_a_failing_bookkeeping_action_follows_the_failure_continuation() -> None:
    g = graph("<Fallback><Sequence><Log/><A/></Sequence><B/></Fallback>")

    assert edges(g) == [
        "START -> A [Log succeeded]",
        "START -> B [Log failed]",
        "A -success-> SUCCESS",
        "A -failure-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_bookkeeping_under_decorators_keeps_their_meaning() -> None:
    g = graph(
        "<Sequence><A/><ForceSuccess><Log/></ForceSuccess><Inverter><Log/></Inverter><B/></Sequence>"
    )

    assert edges(g)[:3] == [
        "START -> A",
        "A -success-> FAILURE [Log succeeded]",
        "A -success-> B [Log failed]",
    ]


def test_two_bookkeeping_nodes_are_two_conditions() -> None:
    g = graph("<Sequence><A/><Log/><Log/><B/></Sequence>")

    guards = [e.guard for e in g.outgoing("a1") if e.target == "a2"]
    assert len(guards) == 1
    assert [lit.condition.node.path for lit in guards[0] if lit.condition.node] == [
        "Sequence/Log",
        "Sequence/Log#2",
    ]


def test_checks_are_not_carried_across_a_bookkeeping_action() -> None:
    # It may write what C reads, so the second check of C stays open.
    g = graph(
        "<Sequence><C/><Note/><Fallback><Sequence><C/><A/></Sequence><B/></Fallback></Sequence>"
    )

    assert edges(g)[:3] == [
        "START -> A [C]",
        "START -> B [C and not C]",
        "START -> FAILURE [not C]",
    ]


def test_bookkeeping_is_not_a_vertex_but_keeps_its_runtime_id() -> None:
    g = graph("<Sequence><A/><Note/><B/></Sequence>")
    flat = flatten(
        parse_string(
            '<root><BehaviorTree ID="T"><Sequence><A/><Note/><B/></Sequence></BehaviorTree></root>',
            config=Config(bookkeeping={"Note": Bookkeeping(never_fails=True)}),
        )
    )

    assert [v.label for v in g.actions] == ["A", "B"]
    assert runtime_ids(flat)[3].type == "Note"
    assert g.vertex_for(3) is None


def test_a_loop_over_bookkeeping_only_is_exact() -> None:
    g = graph(
        "<Sequence><Retrying><Log/></Retrying><A/></Sequence>",
        nodes={"Retrying": "until_success"},
    )

    assert edges(g)[0] == "START -> A [Log succeeded]"
    assert not g.diagnostics


def test_a_skipped_bookkeeping_action_is_skipped() -> None:
    g = graph('<Sequence><A/><Note _skipIf="quiet"/><B/></Sequence>', v4=True)

    assert {e.target for e in g.outgoing("a1") if e.outcome is Outcome.SUCCESS} == {"a2"}


def test_bookkeeping_reduces_the_action_count() -> None:
    xml = '<root><BehaviorTree ID="T"><Sequence><A/><Log/><B/></Sequence></BehaviorTree></root>'
    plain = build_graph(flatten(parse_string(xml)))
    collapsed = build_graph(
        flatten(parse_string(xml, config=Config(bookkeeping={"Log": Bookkeeping()})))
    )

    assert (len(plain.actions), len(collapsed.actions)) == (3, 2)
