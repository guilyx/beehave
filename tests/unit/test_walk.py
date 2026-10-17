"""Walk: turn a flattened tree into an action graph.

Edges are written ``source -outcome-> target [guard]`` so each test reads like
the graph it expects. ``START`` edges have no outcome.
"""

from __future__ import annotations

import pytest

from beehave.config import Config
from beehave.flatten import FlatTree, flatten
from beehave.graph import ActionGraph, Outcome, VertexKind
from beehave.model import Node, NodeKind, Semantics
from beehave.parsers import parse_string
from beehave.walk import build_graph
from tests.conftest import tree_xml

CONDITIONS = Config(conditions=frozenset({"C", "D"}))


def graph(body: str, *, extra: str = "", max_paths: int = 1024) -> ActionGraph:
    doc = parse_string(tree_xml(body, extra=extra), config=CONDITIONS)
    return build_graph(flatten(doc), max_paths=max_paths)


def edges(g: ActionGraph) -> list[str]:
    out = []
    for e in g.edges:
        src, dst = g.vertex(e.source).label, g.vertex(e.target).label
        arrow = f"-{e.outcome.value}->" if e.outcome else "->"
        guard = f" [{' and '.join(map(str, e.guard))}]" if e.guard else ""
        out.append(f"{src} {arrow} {dst}{guard}")
    return out


def test_single_action() -> None:
    assert edges(graph("<A/>")) == [
        "START -> A",
        "A -success-> SUCCESS",
        "A -failure-> FAILURE",
    ]


def test_sequence_runs_the_next_child_on_success() -> None:
    assert edges(graph("<Sequence><A/><B/></Sequence>")) == [
        "START -> A",
        "A -success-> B",
        "A -failure-> FAILURE",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_fallback_runs_the_next_child_on_failure() -> None:
    assert edges(graph("<Fallback><A/><B/></Fallback>")) == [
        "START -> A",
        "A -success-> SUCCESS",
        "A -failure-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_sequence_with_memory_walks_like_a_sequence() -> None:
    assert edges(graph("<SequenceStar><A/><B/></SequenceStar>")) == edges(
        graph("<Sequence><A/><B/></Sequence>")
    )


def test_conditions_become_guards_not_boxes() -> None:
    g = graph("<Sequence><C/><A/></Sequence>")

    assert [v.label for v in g.vertices] == ["START", "A", "SUCCESS", "FAILURE"]
    assert edges(g) == [
        "START -> A [C]",
        "START -> FAILURE [not C]",
        "A -success-> SUCCESS",
        "A -failure-> FAILURE",
    ]


def test_guard_collects_every_condition_on_the_way_in() -> None:
    assert edges(graph("<Sequence><A/><C/><D/><B/></Sequence>"))[:4] == [
        "START -> A",
        "A -success-> B [C and D]",
        "A -success-> FAILURE [C and not D]",
        "A -success-> FAILURE [not C]",
    ]


def test_inverter_swaps_outcomes() -> None:
    # Branches always list the "condition holds" side first.
    assert edges(graph("<Sequence><Inverter><C/></Inverter><A/></Sequence>"))[:2] == [
        "START -> FAILURE [C]",
        "START -> A [not C]",
    ]


def test_force_success_and_force_failure() -> None:
    g = graph(
        "<Sequence><ForceSuccess><A/></ForceSuccess><ForceFailure><B/></ForceFailure></Sequence>"
    )

    assert edges(g) == [
        "START -> A",
        "A -success-> B",
        "A -failure-> B",
        "B -success-> FAILURE",
        "B -failure-> FAILURE",
    ]


@pytest.mark.parametrize(
    "body",
    [
        "<Sequence><AlwaysSuccess/><A/></Sequence>",
        "<Fallback><AlwaysFailure/><A/></Fallback>",
        '<Sequence><SetBlackboard output_key="k" value="1"/><A/></Sequence>',
    ],
)
def test_builtin_plumbing_leaves_are_not_boxes(body: str) -> None:
    assert edges(graph(body)) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]


def test_unreachable_actions_stay_in_the_graph() -> None:
    g = graph("<Sequence><AlwaysFailure/><A/></Sequence>")

    assert edges(g) == ["START -> FAILURE", "A -success-> SUCCESS", "A -failure-> FAILURE"]


def test_if_then_else() -> None:
    assert edges(graph("<IfThenElse><C/><A/><B/></IfThenElse>"))[:2] == [
        "START -> A [C]",
        "START -> B [not C]",
    ]


def test_if_then_without_else_fails() -> None:
    assert edges(graph("<IfThenElse><C/><A/></IfThenElse>"))[:2] == [
        "START -> A [C]",
        "START -> FAILURE [not C]",
    ]


def test_contradictory_paths_are_pruned_and_repeated_checks_merged() -> None:
    g = graph("<Sequence><C/><Fallback><Sequence><C/><A/></Sequence><B/></Fallback></Sequence>")

    assert edges(g)[:2] == ["START -> A [C]", "START -> FAILURE [not C]"]


def test_conditions_with_different_ports_are_different_conditions() -> None:
    g = graph(
        '<Sequence><Probe level="20"/><Fallback><Probe level="50"/><A/></Fallback></Sequence>',
        extra='<TreeNodesModel><Condition ID="Probe"/></TreeNodesModel>',
    )

    assert edges(g)[:3] == [
        "START -> SUCCESS [Probe(level=20) and Probe(level=50)]",
        "START -> A [Probe(level=20) and not Probe(level=50)]",
        "START -> FAILURE [not Probe(level=20)]",
    ]


def test_named_conditions_use_their_name() -> None:
    g = graph('<Sequence><Condition ID="C" name="battery ok" min="3"/><A/></Sequence>')

    assert edges(g)[0] == "START -> A [battery ok]"


def test_switch_branches_on_the_variable() -> None:
    g = graph('<Switch2 variable="{mode}" case_1="AUTO" case_2="MANUAL"><A/><B/><X/></Switch2>')

    assert edges(g)[:3] == [
        "START -> A [mode == AUTO]",
        "START -> B [mode != AUTO and mode == MANUAL]",
        "START -> X [mode != AUTO and mode != MANUAL]",
    ]


def test_blackboard_check_guards_its_child() -> None:
    g = graph(
        '<BlackboardCheckInt value_A="{battery}" value_B="3" return_on_mismatch="SUCCESS">'
        "<A/></BlackboardCheckInt>"
    )

    assert edges(g)[:2] == ["START -> A [battery == 3]", "START -> SUCCESS [battery != 3]"]


def test_blackboard_check_fails_on_mismatch_by_default() -> None:
    g = graph('<BlackboardCheckString value_A="{m}" value_B="go"><A/></BlackboardCheckString>')

    assert edges(g)[:2] == ["START -> A [m == go]", "START -> FAILURE [m != go]"]


def test_subtree_actions_record_where_they_come_from() -> None:
    doc = parse_string(
        tree_xml(
            '<Sequence><A/><SubTreePlus ID="Home" __autoremap="true"/></Sequence>',
            extra='<BehaviorTree ID="Home"><Land/></BehaviorTree>',
        )
    )
    g = build_graph(flatten(doc))

    assert [(v.label, v.subtrees) for v in g.actions] == [("A", ()), ("Land", ("Home",))]


def test_action_ids_follow_document_order() -> None:
    g = graph("<Fallback><Sequence><A/><B/></Sequence><X/></Fallback>")

    assert [(v.id, v.label) for v in g.actions] == [("a1", "A"), ("a2", "B"), ("a3", "X")]
    assert [v.kind for v in g.vertices] == [
        VertexKind.START,
        VertexKind.ACTION,
        VertexKind.ACTION,
        VertexKind.ACTION,
        VertexKind.SUCCESS,
        VertexKind.FAILURE,
    ]


def test_actions_keep_type_ports_and_location() -> None:
    action = graph('<Action ID="Fly" name="go" zone="3"/>').actions[0]

    assert (action.type, action.label, dict(action.ports)) == ("Fly", "go", {"zone": "3"})
    assert action.location is not None


@pytest.mark.parametrize(
    ("decorator", "note"),
    [
        ('<RetryUntilSuccessful num_attempts="3"><A/></RetryUntilSuccessful>', "retry ×3"),
        ('<Repeat num_cycles="2"><A/></Repeat>', "repeat ×2"),
    ],
)
def test_retry_and_repeat_fold_into_a_note_on_the_action(decorator: str, note: str) -> None:
    g = graph(decorator)

    assert g.actions[0].notes == (note,)
    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]


def test_delay_is_transparent_and_exact() -> None:
    g = graph('<Delay delay_msec="5"><A/></Delay>')

    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]
    assert g.diagnostics == ()


def test_switch_without_a_variable_goes_to_the_default() -> None:
    g = graph('<Switch2 case_1="A" case_2="B"><A/><B/><X/></Switch2>')

    assert edges(g)[0] == "START -> X"


@pytest.mark.parametrize(
    ("body", "node_type"),
    [
        ("<ReactiveSequence><C/><A/></ReactiveSequence>", "ReactiveSequence"),
        ("<ReactiveFallback><C/><A/></ReactiveFallback>", "ReactiveFallback"),
        ("<Parallel success_threshold='1'><A/><B/></Parallel>", "Parallel"),
        (
            "<RetryUntilSuccessful num_attempts='2'><A/></RetryUntilSuccessful>",
            "RetryUntilSuccessful",
        ),
        ("<Repeat num_cycles='2'><A/></Repeat>", "Repeat"),
        ("<KeepRunningUntilFailure><A/></KeepRunningUntilFailure>", "KeepRunningUntilFailure"),
        ("<Timeout msec='100'><A/></Timeout>", "Timeout"),
        ("<WhileDoElse><C/><A/><B/></WhileDoElse>", "WhileDoElse"),
        ("<ManualSelector><A/><B/></ManualSelector>", "ManualSelector"),
        ("<Throttle><A/></Throttle>", "Throttle"),
        ("<Vote><A/><B/></Vote>", "Vote"),
    ],
)
def test_nodes_phase_one_cannot_model_exactly_are_reported(body: str, node_type: str) -> None:
    g = graph(body)

    assert [d.node_type for d in g.diagnostics] == [node_type]
    assert g.diagnostics[0].location is not None


def test_reactive_nodes_walk_like_their_plain_versions_for_now() -> None:
    assert edges(
        graph("<ReactiveFallback><Sequence><C/><A/></Sequence><B/></ReactiveFallback>")
    ) == [
        "START -> A [C]",
        "START -> B [not C]",
        "A -success-> SUCCESS",
        "A -failure-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]


def test_parallel_is_approximated_as_a_sequence() -> None:
    assert edges(graph("<Parallel><A/><B/></Parallel>"))[:2] == ["START -> A", "A -success-> B"]


def test_path_explosion_is_capped_and_reported() -> None:
    body = (
        "<Fallback>"
        + "".join(f"<Sequence><C/><D/><P{i}/></Sequence>" for i in range(3))
        + "</Fallback>"
    )
    models = "".join(f'<Condition ID="P{i}"/>' for i in range(3))
    extra = f"<TreeNodesModel>{models}</TreeNodesModel>"

    g = graph(body, extra=extra, max_paths=2)

    start_edges = [e for e in g.edges if e.source == "start"]
    assert len(start_edges) == 2
    assert [d.code for d in g.diagnostics] == ["too-many-paths"]


def test_only_start_edges_have_no_outcome() -> None:
    g = graph("<Sequence><A/><B/></Sequence>")

    assert {e.outcome for e in g.edges if e.source == "start"} == {None}
    assert {e.outcome for e in g.edges if e.source != "start"} == {Outcome.SUCCESS, Outcome.FAILURE}


def test_diagnostics_are_listed_in_document_order() -> None:
    g = graph(
        "<Sequence><ReactiveSequence><C/><A/></ReactiveSequence>"
        "<RetryUntilSuccessful num_attempts='2'><B/></RetryUntilSuccessful></Sequence>"
    )

    assert [d.node_type for d in g.diagnostics] == ["ReactiveSequence", "RetryUntilSuccessful"]


def test_named_diagnostics_say_which_node() -> None:
    g = graph('<ReactiveSequence name="guarded"><C/><A/></ReactiveSequence>')

    assert g.diagnostics[0].message.startswith('ReactiveSequence "guarded": walked like a Sequence')


def test_conditions_of_one_type_with_different_names_are_different_conditions() -> None:
    # A name is the only thing that tells two py_trees instances of one class
    # apart, so merging them would drop real paths.
    g = graph(
        '<Fallback><Sequence><C name="at kitchen"/><A/></Sequence>'
        '<Sequence><C name="at door"/><B/></Sequence></Fallback>'
    )

    assert edges(g)[:3] == [
        "START -> A [at kitchen]",
        "START -> B [not at kitchen and at door]",
        "START -> FAILURE [not at kitchen and not at door]",
    ]


# ------------------------------------------- nodes other formats produce ---


def model_graph(root: Node) -> ActionGraph:
    return build_graph(FlatTree("Main", root, "test", ()))


def act(name: str) -> Node:
    return Node(NodeKind.ACTION, name)


def seq(*children: Node) -> Node:
    return Node(NodeKind.CONTROL, "Sequence", Semantics.SEQUENCE, children=children)


def deco(semantics: Semantics, child: Node, **ports: str) -> Node:
    return Node(
        NodeKind.DECORATOR, semantics.name.title(), semantics, ports=ports, children=(child,)
    )


def test_blackboard_condition_shows_its_expression() -> None:
    check = Node(
        NodeKind.CONDITION,
        "CheckBlackboardVariableValue",
        Semantics.BLACKBOARD_CONDITION,
        "Battery low?",
        {"expression": "battery_level < 20"},
    )

    g = model_graph(seq(check, act("Dock")))

    assert edges(g)[:2] == [
        "START -> Dock [battery_level < 20]",
        "START -> FAILURE [not battery_level < 20]",
    ]
    assert g.edges[0].guard[0].condition.key == "battery_level < 20"


def test_two_checks_of_one_expression_are_one_condition() -> None:
    def check(name: str) -> Node:
        return Node(
            NodeKind.CONDITION,
            "CheckBlackboardVariableValue",
            Semantics.BLACKBOARD_CONDITION,
            name,
            {"expression": "done == True"},
        )

    g = model_graph(
        seq(
            check("Done?"),
            Node(
                NodeKind.CONTROL,
                "Fallback",
                Semantics.FALLBACK,
                children=(check("Done again?"), act("A")),
            ),
        )
    )

    assert edges(g)[:2] == [
        "START -> SUCCESS [done == True]",
        "START -> FAILURE [not done == True]",
    ]


def test_pass_through_is_transparent_and_exact() -> None:
    g = model_graph(deco(Semantics.PASS_THROUGH, act("A")))

    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]
    assert g.diagnostics == ()


def test_an_action_that_never_finishes_has_no_outgoing_edge() -> None:
    idle = Node(NodeKind.ACTION, "Running", Semantics.ALWAYS_RUNNING, "Idle")
    fallback = Node(NodeKind.CONTROL, "Fallback", Semantics.FALLBACK, children=(act("A"), idle))

    g = model_graph(fallback)

    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> Idle"]
    assert g.diagnostics == ()


def test_a_wait_only_succeeds() -> None:
    wait = Node(NodeKind.ACTION, "Timer", Semantics.WAIT, "Wait", {"duration": "2.0"})

    g = model_graph(seq(wait, act("A")))

    assert edges(g) == [
        "START -> Wait",
        "Wait -success-> A",
        "A -success-> SUCCESS",
        "A -failure-> FAILURE",
    ]
    assert g.diagnostics == ()


@pytest.mark.parametrize(
    ("ports", "expected", "message"),
    [
        (
            {"on_success": "FAILURE", "on_failure": "SUCCESS", "on_running": "RUNNING"},
            ["START -> A", "A -success-> FAILURE", "A -failure-> SUCCESS"],
            None,
        ),
        (
            {"on_success": "SUCCESS", "on_failure": "FAILURE", "on_running": "FAILURE"},
            ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"],
            "a RUNNING child is halted and counts as FAILURE; those edges are not shown yet",
        ),
        (
            {"on_success": "RUNNING", "on_failure": "SUCCESS", "on_running": "RUNNING"},
            ["START -> A", "A -success-> SUCCESS", "A -failure-> SUCCESS"],
            "a successful child is ticked again; the loop is not shown yet",
        ),
        (
            {"on_success": "RUNNING", "on_failure": "RUNNING", "on_running": "SUCCESS"},
            ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"],
            (
                "a successful child is ticked again; a failed child is ticked again; "
                "a RUNNING child is halted and counts as SUCCESS; the loop and those edges "
                "are not shown yet"
            ),
        ),
    ],
    ids=["swap", "running-is-failure", "until-failure", "until-running"],
)
def test_status_map(ports: dict[str, str], expected: list[str], message: str | None) -> None:
    g = model_graph(deco(Semantics.STATUS_MAP, act("A"), **ports))

    assert edges(g) == expected
    assert [d.message.split(": ", 1)[1] for d in g.diagnostics] == ([message] if message else [])


def test_run_once_is_transparent_and_reported() -> None:
    g = model_graph(deco(Semantics.RUN_ONCE, act("A"), policy="ON_COMPLETION"))

    assert edges(g) == ["START -> A", "A -success-> SUCCESS", "A -failure-> FAILURE"]
    assert [d.code for d in g.diagnostics] == ["approximated"]


@pytest.mark.parametrize(
    ("semantics", "ports", "note"),
    [
        (Semantics.RETRY, {"num_failures": "3"}, "retry ×3"),
        (Semantics.RETRY, {}, "retry"),
        (Semantics.REPEAT, {"num_success": "2"}, "repeat ×2"),
    ],
)
def test_loop_notes_read_py_trees_counts(
    semantics: Semantics, ports: dict[str, str], note: str
) -> None:
    g = model_graph(deco(semantics, act("A"), **ports))

    assert g.actions[0].notes == (note,)
