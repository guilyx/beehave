"""Presets: custom controls and decorators that behave like a known node (F4a).

Edges are written ``source -outcome-> target [guard]``, as in test_walk.py.
"""

from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Any

import pytest

import beehave
from beehave.config import Config, config_from_dict, load_config
from beehave.errors import ConfigError, ParseError, UnsupportedFormatError
from beehave.flatten import flatten
from beehave.model import NodeKind, Semantics
from beehave.parsers import detect_version, parse_file, parse_string
from beehave.parsers.btcpp_v3 import parse_string as parse_v3
from beehave.presets import PRESETS, NodePreset
from beehave.walk import build_graph

if TYPE_CHECKING:
    from pathlib import Path

    from beehave.graph import ActionGraph

LEAVES = {"conditions": ["C", "D"]}


def config(nodes: dict[str, Any]) -> Config:
    return config_from_dict({**LEAVES, "nodes": nodes})


def graph(body: str, nodes: dict[str, Any] | None = None, *, v4: bool = False) -> ActionGraph:
    marker = ' BTCPP_format="4"' if v4 else ""
    xml = f'<root{marker}><BehaviorTree ID="T">{body}</BehaviorTree></root>'
    document = parse_string(xml, config=config(nodes or {}))
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


def messages(g: ActionGraph) -> list[str]:
    return [d.message for d in g.diagnostics]


# ------------------------------------------------------------------ config ---


def test_config_reads_the_short_and_the_long_form(tmp_path: Path) -> None:
    path = tmp_path / "beehave.yaml"
    path.write_text(
        "nodes:\n"
        "  Pipeline: pipeline_sequence\n"
        "  KeepTrying:\n"
        "    behaves_like: keep_running_until_success\n"
        "  RepeatUntilDone:\n"
        "    behaves_like: loop_until_flag\n"
        "    flag_port: done\n",
        encoding="utf-8",
    )

    assert load_config(path).nodes == {
        "Pipeline": NodePreset("pipeline_sequence"),
        "KeepTrying": NodePreset("until_success"),  # an alias
        "RepeatUntilDone": NodePreset("loop_until_flag", {"flag_port": "done", "exit": "success"}),
    }


@pytest.mark.parametrize(
    ("nodes", "message"),
    [
        (["A"], "'nodes' must map node types to a preset"),
        ({"A": 3}, "give a preset name, or a mapping with 'behaves_like'"),
        ({"A": {"flag_port": "x"}}, "give a preset name"),
        ({"A": "sequence_star"}, "unknown preset 'sequence_star'; one of: fallback, "),
        ({"A": {"behaves_like": "loop_until_flag", "exit": "maybe"}}, "'exit' must be success or"),
        ({"A": {"behaves_like": "loop_until_flag", "flag_port": 1}}, "'flag_port' must be a str"),
        ({"A": {"behaves_like": "sequence", "memory": True}}, "unknown option.*sequence: memory"),
        ({"C": "sequence"}, "listed both as a leaf and under nodes: C"),
    ],
)
def test_invalid_presets_are_refused(nodes: object, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        config_from_dict({**LEAVES, "nodes": nodes})


def test_a_preset_built_in_python_must_exist() -> None:
    with pytest.raises(ConfigError, match="node A: unknown preset 'nope'"):
        Config(nodes={"A": NodePreset("nope")})


def test_declared_lists_every_node_the_config_describes() -> None:
    assert config({"P": "sequence"}).declared == {"C", "D", "P"}


# ---------------------------------------------------------------- parsing ---


def test_a_preset_node_gets_the_preset_kind_and_semantics() -> None:
    doc = parse_string(
        '<root><BehaviorTree ID="T"><Twice><A/></Twice></BehaviorTree></root>',
        config=config({"Twice": "retry"}),
    )

    root = doc.trees["T"].root
    assert (root.kind, root.semantics, root.behaves_like) == (
        NodeKind.DECORATOR,
        Semantics.RETRY,
        "retry",
    )


def test_a_preset_fixes_how_many_children_a_node_takes() -> None:
    with pytest.raises(ParseError, match="<Choose> needs 2 to 3 children, found 1"):
        graph("<Choose><A/></Choose>", {"Choose": "if_then_else"})


def test_a_preset_for_a_built_in_node_is_ignored_with_a_warning() -> None:
    g = graph("<Sequence><A/><Sequence><B/></Sequence></Sequence>", {"Sequence": "fallback"})

    assert edges(g)[:2] == ["START -> A", "A -success-> B"]
    assert [d.code for d in g.diagnostics] == ["preset-ignored"]
    assert "Sequence is a built-in node of BT.CPP v3" in messages(g)[0]


def test_a_v3_project_can_have_its_own_node_named_like_a_v4_one(tmp_path: Path) -> None:
    xml = (
        '<root main_tree_to_execute="T"><BehaviorTree ID="T">'
        "<ParallelAll><A/><B/></ParallelAll></BehaviorTree></root>"
    )
    path = tmp_path / "tree.xml"
    path.write_text(xml, encoding="utf-8")
    declared = config({"ParallelAll": {"behaves_like": "parallel_all"}})

    with pytest.raises(UnsupportedFormatError, match=r"looks like BT\.CPP v4"):
        parse_v3(xml)
    assert detect_version(path) == "4"

    assert detect_version(path, config=declared) == "3"
    document = parse_file(path, config=declared)
    assert document.format == "btcpp-v3"
    node = document.trees["T"].root
    assert (node.semantics, node.behaves_like) == (Semantics.PARALLEL_ALL, "parallel_all")
    g = beehave.analyze(path, config=declared).graph
    assert messages(g) == [
        "ParallelAll (parallel_all): children are shown as if they ran one after another"
    ]


def test_a_preset_name_is_not_taken_for_py_trees_xml() -> None:
    xml = (
        '<root><BehaviorTree ID="T"><Selector memory="true"><A/><B/></Selector>'
        "</BehaviorTree></root>"
    )

    with pytest.raises(UnsupportedFormatError, match="py_trees XML"):
        parse_v3(xml)
    g = build_graph(flatten(parse_v3(xml, config=config({"Selector": "fallback"}))))
    assert edges(g)[:2] == ["START -> A", "A -success-> SUCCESS"]


def test_a_v4_tree_can_use_presets() -> None:
    g = graph("<Pick><A/><B/></Pick>", {"Pick": "fallback"}, v4=True)

    assert edges(g)[:2] == ["START -> A", "A -success-> SUCCESS"]


# ---------------------------------------------------------- exact presets ---

EXACT = [
    ("sequence", "Sequence", "<C/><A/><B/>"),
    ("sequence_with_memory", "SequenceStar", "<A/><C/><B/>"),
    ("fallback", "Fallback", "<C/><A/><B/>"),
    ("if_then_else", "IfThenElse", "<C/><A/><B/>"),
    ("inverter", "Inverter", "<Sequence><C/><A/></Sequence>"),
    ("force_success", "ForceSuccess", "<Sequence><A/><D/></Sequence>"),
    ("force_failure", "ForceFailure", "<A/>"),
    ("pass_through", "Sequence", "<A/>"),
]


@pytest.mark.parametrize(("preset", "builtin", "children"), EXACT)
def test_exact_presets_walk_like_the_node_they_name(
    preset: str, builtin: str, children: str
) -> None:
    custom = graph(f"<Mine>{children}</Mine>", {"Mine": preset})
    reference = graph(f"<{builtin}>{children}</{builtin}>")

    assert PRESETS[preset].exact
    assert edges(custom) == edges(reference)
    assert not custom.diagnostics


def test_try_catch_preset() -> None:
    custom = graph("<Guarded><A/><B/><Clean/></Guarded>", {"Guarded": "try_catch"}, v4=True)

    assert edges(custom) == edges(graph("<TryCatch><A/><B/><Clean/></TryCatch>", v4=True))


# ----------------------------------------------------- approximated presets ---


def test_pipeline_sequence_is_walked_like_a_sequence_and_reported() -> None:
    g = graph("<Pipeline><A/><B/></Pipeline>", {"Pipeline": "pipeline_sequence"})

    assert edges(g) == edges(graph("<Sequence><A/><B/></Sequence>"))
    assert messages(g) == [
        (
            "Pipeline (pipeline_sequence): walked like a Sequence; earlier children are ticked "
            "again while a later one runs, and the edges where they stop it are not shown yet"
        )
    ]


def test_round_robin_is_walked_like_a_fallback_and_reported() -> None:
    g = graph('<Rotate name="r"><A/><B/></Rotate>', {"Rotate": "round_robin"})

    assert edges(g) == edges(graph("<Fallback><A/><B/></Fallback>"))
    assert messages(g) == [
        (
            'Rotate (round_robin) "r": walked like a Fallback from its first child; later '
            "activations start after the child that succeeded last, which is not shown yet"
        )
    ]


def test_a_parallel_that_succeeds_on_the_first_success() -> None:
    g = graph("<Race><A/><B/></Race>", {"Race": "parallel_first_success"})

    assert edges(g) == [
        "START -> A",
        "A -success-> SUCCESS",
        "A -failure-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]
    assert messages(g) == [
        (
            "Race (parallel_first_success): children run at the same time; shown as if they ran "
            "one after another, stopping at the first that succeeds"
        )
    ]


@pytest.mark.parametrize("preset", ["reactive_sequence", "parallel", "parallel_all"])
def test_presets_of_approximated_built_ins_are_reported_too(preset: str) -> None:
    g = graph("<Mine><A/><B/></Mine>", {"Mine": preset})

    assert [d.code for d in g.diagnostics] == ["approximated"]
    assert messages(g)[0].startswith(f"Mine ({preset}): ")


# ------------------------------------------------------------------- loops ---


def test_until_success_never_fails() -> None:
    g = graph(
        "<Sequence><KeepTrying><A/></KeepTrying><B/></Sequence>", {"KeepTrying": "until_success"}
    )

    assert edges(g) == [
        "START -> A",
        "A -success-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]
    assert g.vertex("a1").notes == ("until success",)
    assert messages(g) == [
        (
            "KeepTrying (until_success): a failed child is ticked again until it succeeds, so it "
            "never fails; the edges back to the child are not shown yet"
        )
    ]


def test_polling_a_condition_is_exact() -> None:
    g = graph(
        "<Sequence><WaitUntil><C/></WaitUntil><B/></Sequence>", {"WaitUntil": "poll_until_success"}
    )

    assert edges(g) == [
        "START -> B [C]",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]
    assert not g.diagnostics


def test_loop_until_flag_exits_when_the_flag_is_set() -> None:
    nodes = {"RepeatUntilDone": {"behaves_like": "loop_until_flag", "flag_port": "done"}}

    g = graph(
        '<Sequence><RepeatUntilDone done="{finished}"><A/></RepeatUntilDone><B/></Sequence>',
        nodes,
    )

    assert edges(g) == [
        "START -> B [finished]",
        "START -> A [!finished]",
        "A -success-> B [finished]",
        "A -failure-> FAILURE",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]
    assert messages(g) == [
        (
            "RepeatUntilDone (loop_until_flag): the child is ticked again until finished is set; "
            "the edges back to the child are not shown yet"
        )
    ]
    flag = g.edges[0].guard[0].condition
    assert flag.node is not None
    assert flag.node.path == "Sequence/RepeatUntilDone"


def test_loop_until_flag_can_exit_with_failure() -> None:
    nodes = {"Abort": {"behaves_like": "loop_until_flag", "exit": "failure"}}

    g = graph('<Fallback><Abort flag="{abort}"><C/></Abort><B/></Fallback>', nodes)

    assert edges(g) == [
        "START -> B [abort]",
        "START -> B [!abort and not C]",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]
    assert not g.diagnostics  # its child runs no action: nothing is missing


def test_loop_until_flag_reads_the_flag_through_subtrees() -> None:
    xml = (
        '<root main_tree_to_execute="T"><BehaviorTree ID="T">'
        '<SubTreePlus ID="Inner" stop="{mission_over}"/></BehaviorTree>'
        '<BehaviorTree ID="Inner"><Loop flag="{stop}"><A/></Loop></BehaviorTree></root>'
    )
    g = build_graph(flatten(parse_string(xml, config=config({"Loop": "loop_until_flag"}))))

    assert edges(g)[0] == "START -> SUCCESS [mission_over]"


def test_loop_until_flag_without_its_port_is_an_error() -> None:
    g = graph("<Loop><A/></Loop>", {"Loop": "loop_until_flag"})

    assert edges(g) == ["START -> A", "A -failure-> FAILURE"]
    assert [d.code for d in g.diagnostics] == ["runtime-error", "approximated"]
    assert (
        messages(g)[0] == "Loop (loop_until_flag): no port 'flag' holds the flag; it is never set"
    )


def test_a_skipped_child_keeps_the_loop_going() -> None:
    g = graph(
        '<Sequence><Loop flag="{done}"><A _skipIf="paused"/></Loop><B/></Sequence>',
        {"Loop": "loop_until_flag"},
        v4=True,
    )

    assert "SKIPPED" not in [v.label for v in g.vertices]
    assert "START -> B [done]" in edges(g)


def test_v4_built_ins_win_over_presets() -> None:
    g = graph("<SequenceStar><A/></SequenceStar>", {"SequenceStar": "fallback"}, v4=True)

    assert [d.code for d in g.diagnostics] == ["v3-name", "preset-ignored"]
    assert "built-in node of BT.CPP v4" in messages(g)[1]
