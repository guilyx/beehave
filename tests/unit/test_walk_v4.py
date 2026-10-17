"""Walk BT.CPP v4 trees: SKIPPED, pre-conditions, scripts and the v4 nodes.

Edges are written ``source -outcome-> target [guard]``, as in test_walk.py.
"""

from __future__ import annotations

import pytest

import beehave
from beehave.diagnostics import Severity
from beehave.flatten import flatten
from beehave.graph import ActionGraph, VertexKind
from beehave.parsers.btcpp_v4 import parse_string
from beehave.walk import build_graph

MODELS = '<TreeNodesModel><Condition ID="C"/><Condition ID="D"/></TreeNodesModel>'


def graph(body: str) -> ActionGraph:
    xml = (
        '<root BTCPP_format="4" main_tree_to_execute="Main">'
        f'<BehaviorTree ID="Main">{body}</BehaviorTree>{MODELS}</root>'
    )
    return build_graph(flatten(parse_string(xml)))


def edges(g: ActionGraph) -> list[str]:
    out = []
    for e in g.edges:
        src, dst = g.vertex(e.source).label, g.vertex(e.target).label
        arrow = f"-{e.outcome.value}->" if e.outcome else "->"
        guard = f" [{' and '.join(map(str, e.guard))}]" if e.guard else ""
        out.append(f"{src} {arrow} {dst}{guard}")
    return out


def messages(g: ActionGraph) -> list[str]:
    return [d.message for d in g.diagnostics]


# ----------------------------------------------------------------- SKIPPED ---


def test_a_tree_that_cannot_skip_has_no_skipped_vertex() -> None:
    g = graph("<Sequence><C/><A/></Sequence>")

    assert edges(g) == [
        "START -> A [C]",
        "START -> FAILURE [not C]",
        "A -success-> SUCCESS",
        "A -failure-> FAILURE",
    ]
    assert VertexKind.SKIPPED not in {v.kind for v in g.vertices}


def test_a_sequence_skips_only_when_every_child_skips() -> None:
    # The worked example of docs/research/btcpp-v4-xml.md §3.3.
    g = graph('<Sequence><Charge _skipIf="battery &gt; 80"/><Patrol _skipIf="!ready"/></Sequence>')

    assert edges(g) == [
        "START -> SKIPPED [battery > 80 and !ready]",
        "START -> Patrol [battery > 80 and ready]",
        "START -> Charge [!(battery > 80)]",
        "Charge -success-> SUCCESS [!ready]",
        "Charge -success-> Patrol [ready]",
        "Charge -failure-> FAILURE",
        "Patrol -success-> SUCCESS",
        "Patrol -failure-> FAILURE",
    ]
    assert g.vertex("skipped").kind is VertexKind.SKIPPED


def test_a_fallback_moves_past_a_skipped_child() -> None:
    g = graph('<Fallback><A _skipIf="x"/><B/></Fallback>')

    assert edges(g) == [
        "START -> B [x]",
        "START -> A [!x]",
        "A -success-> SUCCESS",
        "A -failure-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_a_fallback_whose_children_all_skip_skips() -> None:
    g = graph('<Fallback><A _skipIf="x"/><B _skipIf="y"/></Fallback>')

    assert edges(g)[:3] == [
        "START -> SKIPPED [x and y]",
        "START -> B [x and !y]",
        "START -> A [!x]",
    ]
    assert edges(g)[4:6] == ["A -failure-> FAILURE [y]", "A -failure-> B [!y]"]


def test_parallel_with_every_child_skipped_succeeds_by_default() -> None:
    g = graph('<Parallel><A _skipIf="x"/><B _skipIf="y"/></Parallel>')

    assert edges(g)[0] == "START -> SUCCESS [x and y]"


def test_parallel_with_a_success_count_skips() -> None:
    g = graph('<Parallel success_count="2"><A _skipIf="x"/><B _skipIf="y"/></Parallel>')

    assert edges(g)[0] == "START -> SKIPPED [x and y]"


def test_parallel_all_with_every_child_skipped_skips() -> None:
    g = graph('<ParallelAll><A _skipIf="x"/><B _skipIf="y"/></ParallelAll>')

    assert edges(g)[0] == "START -> SKIPPED [x and y]"
    assert "ParallelAll: children are shown as if they ran one after another" in messages(g)


def test_decorators_pass_skipped_through() -> None:
    g = graph('<Inverter><A _skipIf="x"/></Inverter>')

    assert edges(g) == [
        "START -> SKIPPED [x]",
        "START -> A [!x]",
        "A -success-> FAILURE",
        "A -failure-> SUCCESS",
    ]


def test_the_skipped_vertex_renders_everywhere() -> None:
    g = graph('<A _skipIf="x"/>')

    assert "START --[x]--> SKIPPED" in beehave.to_text(g)
    assert 'skipped(["SKIPPED"])' in beehave.to_mermaid(g)
    assert '"skipped"' in beehave.to_dot(g)
    assert '"kind": "skipped"' in beehave.to_json(g)


# ---------------------------------------------------------- pre-conditions ---


def test_pre_conditions_are_checked_in_order() -> None:
    g = graph('<A _failureIf="f" _successIf="s" _skipIf="k" _while="w"/>')

    assert edges(g)[:5] == [
        "START -> FAILURE [f]",
        "START -> SUCCESS [!f and s]",
        "START -> SKIPPED [!f and !s and k]",
        "START -> A [!f and !s and !k and w]",
        "START -> SKIPPED [!f and !s and !k and !w]",
    ]


def test_while_is_reported() -> None:
    g = graph('<A _while="armed"/>')

    assert messages(g) == [
        "A: _while is checked on every tick; the interrupt edges are not shown yet"
    ]


def test_post_conditions_do_not_change_the_edges() -> None:
    g = graph('<A _onSuccess="done := true" _onFailure="tries += 1" _post="x := 0"/>')

    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]


def test_conditions_on_a_control_node_wrap_it() -> None:
    g = graph('<Sequence _skipIf="!armed"><A/><B/></Sequence>')

    assert edges(g)[:2] == ["START -> SKIPPED [!armed]", "START -> A [armed]"]


# ----------------------------------------------------------------- scripts ---


def test_script_condition_is_a_guard() -> None:
    g = graph('<Sequence><ScriptCondition code="battery  &lt;\n 20"/><Dock/></Sequence>')

    assert edges(g)[:2] == ["START -> Dock [battery < 20]", "START -> FAILURE [!(battery < 20)]"]


def test_one_script_written_two_ways_is_one_condition() -> None:
    g = graph(
        '<Sequence><ScriptCondition code="battery&lt;20"/>'
        '<Fallback><ScriptCondition code="battery &lt; 20"/><A/></Fallback></Sequence>'
    )

    assert edges(g)[:2] == ["START -> SUCCESS [battery<20]", "START -> FAILURE [!(battery<20)]"]


def test_a_script_runs_and_succeeds_without_a_box() -> None:
    g = graph('<Sequence><Script code="tries := 0"/><A/></Sequence>')

    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]


def test_guards_are_not_merged_across_a_write() -> None:
    # The script may change x between the two checks, so the second check is
    # not decided by the first one.
    g = graph(
        '<Sequence><ScriptCondition code="x == 0"/><Script code="x := 1"/>'
        '<Fallback><Sequence><ScriptCondition code="x == 0"/><A/></Sequence><B/></Fallback>'
        "</Sequence>"
    )

    assert edges(g)[:3] == [
        "START -> A [x == 0]",
        "START -> B [x == 0 and !(x == 0)]",
        "START -> FAILURE [!(x == 0)]",
    ]


# --------------------------------------------------------------- v4 nodes ---


def test_try_catch_runs_the_catch_child_then_fails() -> None:
    g = graph("<TryCatch><A/><B/><Cleanup/></TryCatch>")

    assert edges(g) == [
        "START -> A",
        "A -success-> B",
        "A -failure-> Cleanup",
        "B -success-> SUCCESS",
        "B -failure-> Cleanup",
        "Cleanup -success-> FAILURE",
        "Cleanup -failure-> FAILURE",
    ]
    assert g.diagnostics == ()


@pytest.mark.parametrize(
    ("otherwise", "expected"),
    [
        ("", ["START -> A [ok]", "START -> FAILURE [!ok]"]),
        (' else="SUCCESS"', ["START -> A [ok]", "START -> SUCCESS [!ok]"]),
        (' else="SKIPPED"', ["START -> A [ok]", "START -> SKIPPED [!ok]"]),
        (' else="RUNNING"', ["START -> A [ok]"]),
    ],
    ids=["failure", "success", "skipped", "running"],
)
def test_precondition(otherwise: str, expected: list[str]) -> None:
    g = graph(f'<Precondition if="ok"{otherwise}><A/></Precondition>')

    assert edges(g)[: len(expected)] == expected
    assert g.diagnostics == ()


def test_precondition_else_idle_is_a_runtime_error() -> None:
    g = graph('<Precondition if="ok" else="IDLE"><A/></Precondition>')

    assert edges(g)[0] == "START -> A [ok]"
    assert len([e for e in g.edges if e.source == "start"]) == 1
    (diagnostic,) = g.diagnostics
    assert (diagnostic.code, diagnostic.severity) == ("runtime-error", Severity.ERROR)


def test_if_then_else_with_a_skippable_condition_is_a_runtime_error() -> None:
    g = graph('<IfThenElse><C _skipIf="x"/><A/><B/></IfThenElse>')

    assert edges(g)[:2] == ["START -> A [!x and C]", "START -> B [!x and not C]"]
    assert [d.code for d in g.diagnostics] == ["runtime-error"]
    assert "a skipped first child makes BT.CPP throw" in g.diagnostics[0].message


def test_skip_unless_updated() -> None:
    g = graph('<SkipUnlessUpdated entry="{goal}"><Replan/></SkipUnlessUpdated>')

    assert edges(g)[:2] == ["START -> Replan [goal updated]", "START -> SKIPPED [not goal updated]"]


def test_entry_updated_checks_are_one_per_node() -> None:
    # Each node remembers the last version it saw, so two checks of one entry
    # are two conditions.
    g = graph(
        '<Sequence><WasEntryUpdated entry="{goal}"/>'
        '<Fallback><WasEntryUpdated entry="{goal}"/><A/></Fallback></Sequence>'
    )

    assert len([e for e in g.edges if e.source == "start"]) == 3


def test_sleep_only_succeeds() -> None:
    g = graph('<Sequence><Sleep msec="500"/><A/></Sequence>')

    assert edges(g) == [
        "START -> Sleep",
        "Sleep -success-> A",
        "A -success-> SUCCESS",
        "A -failure-> FAILURE",
    ]


def test_loop_over_a_queue() -> None:
    g = graph('<LoopString queue="{waypoints}" value="{wp}"><Visit/></LoopString>')

    assert edges(g) == [
        "START -> Visit [waypoints has items]",
        "START -> SUCCESS [not waypoints has items]",
        "Visit -success-> SUCCESS",
        "Visit -failure-> FAILURE",
    ]
    assert g.actions[0].notes == ("loop",)
    assert [d.code for d in g.diagnostics] == ["approximated"]


def test_loop_over_an_empty_queue_can_skip() -> None:
    g = graph('<LoopInt queue="{q}" if_empty="SKIPPED"><Visit/></LoopInt>')

    assert edges(g)[1] == "START -> SKIPPED [not q has items]"


@pytest.mark.parametrize("tag", ["AsyncSequence", "AsyncFallback"])
def test_async_nodes_are_exact(tag: str) -> None:
    assert graph(f"<{tag}><A/><B/></{tag}>").diagnostics == ()


def test_wait_value_update_waits_then_ticks_its_child() -> None:
    g = graph('<WaitValueUpdate entry="{goal}"><Replan/></WaitValueUpdate>')

    assert edges(g) == ["START -> Replan", "Replan -success-> SUCCESS", "Replan -failure-> FAILURE"]
    assert g.diagnostics == ()


def test_an_outcome_that_depends_on_skipped_siblings_is_reported() -> None:
    # After Visit, the loop returns SKIPPED; whether the Sequence then skips
    # depends on whether A was skipped before it. Phase 1 draws one case.
    g = graph(
        '<Sequence><A _skipIf="x"/>'
        '<LoopInt queue="{q}" if_empty="SKIPPED"><Visit/></LoopInt></Sequence>'
    )

    assert any("only one case is drawn" in m for m in messages(g))


@pytest.mark.parametrize(
    ("body", "skipped"),
    [
        (
            '<Switch2 variable="{mode}" case_1="a" case_2="b"><A _skipIf="x"/><B/><D/></Switch2>',
            "mode == a and x",
        ),
        ('<IfThenElse><C/><A _skipIf="x"/><B/></IfThenElse>', "C and x"),
        ('<TryCatch><A _skipIf="x"/><Cleanup/></TryCatch>', "x"),
        ('<Precondition if="ok" else="SKIPPED"><A/></Precondition>', "!ok"),
    ],
    ids=["switch", "if-then-else", "try-catch", "precondition"],
)
def test_a_skipped_child_moves_a_fallback_on(body: str, skipped: str) -> None:
    g = graph(f"<Fallback>{body}<Next/></Fallback>")

    assert f"START -> Next [{skipped}]" in edges(g)


def test_a_parallel_success_count_that_is_a_key_is_not_positive() -> None:
    g = graph('<Parallel success_count="{n}"><A _skipIf="x"/><B _skipIf="y"/></Parallel>')

    assert edges(g)[0] == "START -> SUCCESS [x and y]"
