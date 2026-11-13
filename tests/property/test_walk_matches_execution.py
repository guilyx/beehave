"""The action graph must agree with actually running the tree.

Hypothesis generates random trees made of the node types Phase 1 models
exactly, plus random values for every condition and random outcomes for every
action. A small reference interpreter runs the tree; following the action graph
with the same values must visit the same actions, in the same order, and end
with the same result. At every step exactly one outgoing edge must match, so
the guards are both complete and mutually exclusive.

The same holds for BT.CPP v4 trees where any node may be skipped, and a v3
tree written as v4 must give the same graph.

Every step also names the node it stands for: the runtime id of each action the
graph visits, and of each condition in the guards it follows, is the id of a
node the interpreter ticked at that point.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from hypothesis import given, settings
from hypothesis import strategies as st

from beehave.config import Config, config_from_dict
from beehave.flatten import flatten
from beehave.graph import FAILURE, SKIPPED, START, SUCCESS, ActionGraph, Outcome
from beehave.hashing import graph_hash
from beehave.model import Node, NodeKind, Semantics
from beehave.parsers import parse_string
from beehave.parsers.btcpp_v4 import parse_string as parse_v4
from beehave.walk import build_graph

if TYPE_CHECKING:
    from collections.abc import Sequence

CONDITIONS = ("C0", "C1", "C2")
CONFIG = Config(conditions=frozenset(CONDITIONS))

# --------------------------------------------------------- tree generator ---

Spec: TypeAlias = "tuple[str] | tuple[str, list[Spec]]"

_LEAVES = st.sampled_from(
    [
        ("Act",),
        ("Act",),
        ("Act",),
        *((c,) for c in CONDITIONS),
        ("AlwaysSuccess",),
        ("AlwaysFailure",),
    ]
)


def _extend(children: st.SearchStrategy[Spec]) -> st.SearchStrategy[Spec]:
    return st.one_of(
        st.tuples(
            st.sampled_from(["Sequence", "SequenceStar", "Fallback"]),
            st.lists(children, min_size=1, max_size=4),
        ),
        st.tuples(
            st.sampled_from(["Inverter", "ForceSuccess", "ForceFailure"]),
            children.map(lambda c: [c]),
        ),
        st.tuples(st.just("IfThenElse"), st.lists(children, min_size=2, max_size=3)),
    )


TREES: st.SearchStrategy[Spec] = st.recursive(_LEAVES, _extend, max_leaves=14)


def to_xml(spec: Spec) -> str:
    if len(spec) == 1:
        return f"<{spec[0]}/>"
    name, children = spec[0], spec[1]
    return f"<{name}>{''.join(to_xml(c) for c in children)}</{name}>"


# ------------------------------------------------- reference interpreter ---


@dataclass
class Run:
    conditions: dict[str, bool]
    outcomes: Sequence[bool]
    action_index: dict[int, int]
    trace: list[int] = field(default_factory=list)
    preorder: dict[int, int] = field(default_factory=dict)
    ticks: list[tuple[str, int]] = field(default_factory=list)
    """``("condition" | "action", pre-order index)`` for every leaf ticked."""

    def tick(self, node: Node) -> bool:
        sem = node.semantics
        if node.kind is NodeKind.CONDITION:
            self.ticks.append(("condition", self.preorder[id(node)]))
            return self.conditions[node.type]
        if node.kind is NodeKind.ACTION:
            if sem is Semantics.ALWAYS_SUCCESS:
                return True
            if sem is Semantics.ALWAYS_FAILURE:
                return False
            index = self.action_index[id(node)]
            self.trace.append(index)
            self.ticks.append(("action", self.preorder[id(node)]))
            return self.outcomes[index]
        if node.kind is NodeKind.SUBTREE:
            return self.tick(node.children[0])
        if sem in (Semantics.SEQUENCE, Semantics.SEQUENCE_WITH_MEMORY):
            return all(self.tick(c) for c in node.children)
        if sem is Semantics.FALLBACK:
            return any(self.tick(c) for c in node.children)
        if sem is Semantics.INVERTER:
            return not self.tick(node.children[0])
        if sem is Semantics.FORCE_SUCCESS:
            self.tick(node.children[0])
            return True
        if sem is Semantics.FORCE_FAILURE:
            self.tick(node.children[0])
            return False
        if sem is Semantics.IF_THEN_ELSE:
            if self.tick(node.children[0]):
                return self.tick(node.children[1])
            return len(node.children) == 3 and self.tick(node.children[2])
        raise AssertionError(sem)


def run_tree(
    root: Node, conditions: dict[str, bool], outcomes: Sequence[bool]
) -> tuple[list[int], bool]:
    actions = [
        n for n in root.walk() if n.kind is NodeKind.ACTION and n.semantics is Semantics.CUSTOM
    ]
    preorder = {id(n): i for i, n in enumerate(root.walk())}
    run = Run(conditions, outcomes, {id(n): i for i, n in enumerate(actions)}, preorder=preorder)
    result = run.tick(root)
    return run.trace, result


# ---------------------------------------------------------- graph follower ---


def follow(
    graph: ActionGraph, conditions: dict[str, bool], outcomes: Sequence[bool]
) -> tuple[list[int], bool]:
    index = {v.id: i for i, v in enumerate(graph.actions)}
    holds = {f"{name}()": value for name, value in conditions.items()}
    trace: list[int] = []
    current = START
    while True:
        outcome = None
        if current != START:
            outcome = Outcome.SUCCESS if outcomes[index[current]] else Outcome.FAILURE
        matching = [
            e
            for e in graph.outgoing(current)
            if e.outcome == outcome
            and all(holds[lit.condition.key] == lit.positive for lit in e.guard)
        ]
        assert len(matching) == 1, f"{len(matching)} edges match out of {current}"
        current = matching[0].target
        if current in (SUCCESS, FAILURE):
            return trace, current == SUCCESS
        assert len(trace) <= len(graph.actions), "the graph loops"
        trace.append(index[current])


# ------------------------------------------------------------ properties ---


@settings(max_examples=300, deadline=None)
@given(spec=TREES, data=st.data())
def test_graph_agrees_with_execution(spec: Spec, data: st.DataObject) -> None:
    xml = f'<root><BehaviorTree ID="T">{to_xml(spec)}</BehaviorTree></root>'
    flat = flatten(parse_string(xml, config=CONFIG))
    graph = build_graph(flat)

    conditions = {c: data.draw(st.booleans(), label=c) for c in CONDITIONS}
    outcomes = data.draw(
        st.lists(st.booleans(), min_size=len(graph.actions), max_size=len(graph.actions))
    )

    assert follow(graph, conditions, outcomes) == run_tree(flat.root, conditions, outcomes)


def follow_ids(
    graph: ActionGraph, conditions: dict[str, bool], outcomes: Sequence[bool]
) -> list[tuple[set[int], int | None]]:
    """For each step: the runtime ids of the guard's conditions, then of the action."""
    index = {v.id: i for i, v in enumerate(graph.actions)}
    holds = {f"{name}()": value for name, value in conditions.items()}
    steps: list[tuple[set[int], int | None]] = []
    current = START
    while current not in (SUCCESS, FAILURE):
        outcome = None
        if current != START:
            outcome = Outcome.SUCCESS if outcomes[index[current]] else Outcome.FAILURE
        edge = next(
            e
            for e in graph.outgoing(current)
            if e.outcome == outcome
            and all(holds[lit.condition.key] == lit.positive for lit in e.guard)
        )
        checked = {lit.condition.node.index for lit in edge.guard if lit.condition.node}
        assert len(checked) == len(edge.guard), "a guard condition has no node"
        current = edge.target
        node = graph.vertex(current).node
        steps.append((checked, node.index if node else None))
    return steps


@settings(max_examples=300, deadline=None)
@given(spec=TREES, data=st.data())
def test_graph_steps_name_the_nodes_the_interpreter_ticks(spec: Spec, data: st.DataObject) -> None:
    xml = f'<root><BehaviorTree ID="T">{to_xml(spec)}</BehaviorTree></root>'
    flat = flatten(parse_string(xml, config=CONFIG))
    graph = build_graph(flat)
    conditions = {c: data.draw(st.booleans(), label=c) for c in CONDITIONS}
    outcomes = data.draw(
        st.lists(st.booleans(), min_size=len(graph.actions), max_size=len(graph.actions))
    )
    actions = [
        n for n in flat.root.walk() if n.kind is NodeKind.ACTION and n.semantics is Semantics.CUSTOM
    ]
    preorder = {id(n): i for i, n in enumerate(flat.root.walk())}
    run = Run(conditions, outcomes, {id(n): i for i, n in enumerate(actions)}, preorder=preorder)
    run.tick(flat.root)

    # Split the interpreter's ticks at each action: the conditions checked
    # before it, then the action itself; the last group ends the run.
    expected: list[tuple[set[int], int | None]] = []
    checked: set[int] = set()
    for kind, node_id in run.ticks:
        if kind == "condition":
            checked.add(node_id)
        else:
            expected.append((checked, node_id))
            checked = set()
    expected.append((checked, None))

    steps = follow_ids(graph, conditions, outcomes)
    assert [action for _, action in steps] == [action for _, action in expected]
    for (guard, _), (ticked, _) in zip(steps, expected, strict=True):
        assert guard <= ticked, "a guard names a condition the interpreter did not tick"


@settings(max_examples=200, deadline=None)
@given(spec=TREES)
def test_graph_is_deterministic_and_well_formed(spec: Spec) -> None:
    xml = f'<root><BehaviorTree ID="T">{to_xml(spec)}</BehaviorTree></root>'
    flat = flatten(parse_string(xml, config=CONFIG))
    graph = build_graph(flat)

    assert graph == build_graph(flat)
    ids = {v.id for v in graph.vertices}
    for edge in graph.edges:
        assert {edge.source, edge.target} <= ids
        keys = [(lit.condition.key, lit.positive) for lit in edge.guard]
        assert len({k for k, _ in keys}) == len(keys), "a condition appears twice in one guard"
    for action in graph.actions:
        outcomes = {e.outcome for e in graph.outgoing(action.id)}
        assert outcomes == {Outcome.SUCCESS, Outcome.FAILURE}
    assert not graph.diagnostics


# ---------------------------------------------------- BT.CPP v4: SKIPPED ---

SKIPS = ("k0", "k1")

Spec4: TypeAlias = "tuple[str, tuple[Spec4, ...], str | None]"

_SKIP = st.sampled_from([None, None, None, *SKIPS])
_LEAVES_V4 = st.tuples(
    st.sampled_from(["Act", "Act", "Act", *CONDITIONS, "AlwaysSuccess", "AlwaysFailure"]),
    st.just(()),
    _SKIP,
)


def _extend_v4(children: st.SearchStrategy[Spec4]) -> st.SearchStrategy[Spec4]:
    return st.one_of(
        st.tuples(
            st.sampled_from(["Sequence", "SequenceWithMemory", "Fallback"]),
            st.lists(children, min_size=1, max_size=4).map(tuple),
            _SKIP,
        ),
        st.tuples(
            st.sampled_from(["Inverter", "ForceSuccess", "ForceFailure"]),
            children.map(lambda c: (c,)),
            _SKIP,
        ),
    )


TREES_V4: st.SearchStrategy[Spec4] = st.recursive(_LEAVES_V4, _extend_v4, max_leaves=12)


def to_xml_v4(spec: Spec4) -> str:
    name, children, skip = spec
    attr = f' _skipIf="{skip}"' if skip else ""
    if not children:
        return f"<{name}{attr}/>"
    return f"<{name}{attr}>{''.join(to_xml_v4(c) for c in children)}</{name}>"


@dataclass
class Run4:
    """A reference interpreter for BT.CPP v4 that knows SKIPPED ("K")."""

    values: dict[str, bool]
    outcomes: Sequence[bool]
    action_index: dict[int, int]
    trace: list[int] = field(default_factory=list)

    def tick(self, node: Node) -> str:
        skip = node.scripts.get("_skipIf")
        if skip is not None and self.values[skip]:
            return "K"
        sem = node.semantics
        if node.kind is NodeKind.CONDITION:
            return "S" if self.values[node.type] else "F"
        if node.kind is NodeKind.ACTION:
            if sem is Semantics.ALWAYS_SUCCESS:
                return "S"
            if sem is Semantics.ALWAYS_FAILURE:
                return "F"
            index = self.action_index[id(node)]
            self.trace.append(index)
            return "S" if self.outcomes[index] else "F"
        if sem in (Semantics.SEQUENCE, Semantics.SEQUENCE_WITH_MEMORY, Semantics.FALLBACK):
            stop = "F" if sem is not Semantics.FALLBACK else "S"
            ran = False
            for child in node.children:
                result = self.tick(child)
                if result == stop:
                    return stop
                ran = ran or result != "K"
            # Only a node whose children were all skipped is skipped.
            return ("F" if stop == "S" else "S") if ran else "K"
        result = self.tick(node.children[0])
        if result == "K":
            return "K"
        if sem is Semantics.INVERTER:
            return "F" if result == "S" else "S"
        return "S" if sem is Semantics.FORCE_SUCCESS else "F"


def follow4(
    graph: ActionGraph, values: dict[str, bool], outcomes: Sequence[bool]
) -> tuple[list[int], str]:
    index = {v.id: i for i, v in enumerate(graph.actions)}
    holds = {f"{c}()": values[c] for c in CONDITIONS} | {k: values[k] for k in SKIPS}
    trace: list[int] = []
    current = START
    ends = {SUCCESS: "S", FAILURE: "F", SKIPPED: "K"}
    while True:
        outcome = None
        if current != START:
            outcome = Outcome.SUCCESS if outcomes[index[current]] else Outcome.FAILURE
        matching = [
            e
            for e in graph.outgoing(current)
            if e.outcome == outcome
            and all(holds[lit.condition.key] == lit.positive for lit in e.guard)
        ]
        assert len(matching) == 1, f"{len(matching)} edges match out of {current}"
        current = matching[0].target
        if current in ends:
            return trace, ends[current]
        assert len(trace) <= len(graph.actions), "the graph loops"
        trace.append(index[current])


@settings(max_examples=300, deadline=None)
@given(spec=TREES_V4, data=st.data())
def test_graph_agrees_with_execution_when_nodes_skip(spec: Spec4, data: st.DataObject) -> None:
    xml = f'<root BTCPP_format="4"><BehaviorTree ID="T">{to_xml_v4(spec)}</BehaviorTree></root>'
    flat = flatten(parse_v4(xml, config=CONFIG))
    graph = build_graph(flat)

    values = {name: data.draw(st.booleans(), label=name) for name in (*CONDITIONS, *SKIPS)}
    outcomes = data.draw(
        st.lists(st.booleans(), min_size=len(graph.actions), max_size=len(graph.actions))
    )
    actions = [
        n for n in flat.root.walk() if n.kind is NodeKind.ACTION and n.semantics is Semantics.CUSTOM
    ]
    run = Run4(values, outcomes, {id(n): i for i, n in enumerate(actions)})
    result = run.tick(flat.root)

    assert follow4(graph, values, outcomes) == (run.trace, result)


@settings(max_examples=200, deadline=None)
@given(spec=TREES)
def test_a_v3_tree_written_as_v4_gives_the_same_graph(spec: Spec) -> None:
    body = to_xml(spec)
    v3 = f'<root><BehaviorTree ID="T">{body}</BehaviorTree></root>'
    v4 = (
        '<root BTCPP_format="4"><BehaviorTree ID="T">'
        f"{body.replace('SequenceStar', 'SequenceWithMemory')}</BehaviorTree></root>"
    )

    graph_v3 = build_graph(flatten(parse_string(v3, config=CONFIG)))
    graph_v4 = build_graph(flatten(parse_v4(v4, config=CONFIG)))

    assert (graph_v4.vertices, graph_v4.edges) == (graph_v3.vertices, graph_v3.edges)
    assert graph_hash(graph_v4) == graph_hash(graph_v3)


@settings(max_examples=200, deadline=None)
@given(spec=TREES, other=TREES)
def test_graph_hashes_agree_with_graph_equality(spec: Spec, other: Spec) -> None:
    def graph(body: Spec) -> ActionGraph:
        xml = f'<root><BehaviorTree ID="T">{to_xml(body)}</BehaviorTree></root>'
        return build_graph(flatten(parse_string(xml, config=CONFIG)))

    a, b = graph(spec), graph(other)

    same_graph = (a.vertices, a.edges) == (b.vertices, b.edges)
    assert (graph_hash(a) == graph_hash(b)) == same_graph


# ------------------------------------------- presets: custom nodes and loops ---

# Custom nodes the config gives a preset. The loops never end when nothing
# changes between iterations, and in these runs nothing does (every condition
# and every action keeps its value), so a loop either ends in its first pass
# or never: the interpreter reports that as "stuck", and the graph has no edge
# to follow at that point.
PRESET_CONFIG = config_from_dict(
    {
        "conditions": list(CONDITIONS),
        "nodes": {
            "MySequence": "sequence",
            "MyFallback": "fallback",
            "MyChoice": "if_then_else",
            "MyInverter": "inverter",
            "KeepTrying": "until_success",
            "WaitFor": "poll_until_success",
            "RepeatUntil": {"behaves_like": "loop_until_flag", "flag_port": "until"},
            "RepeatOrFail": {"behaves_like": "loop_until_flag", "exit": "failure"},
        },
    }
)
FLAGS = ("F0", "F1")


class Stuck(Exception):  # noqa: N818 - an outcome, not an error
    """The tree ticks the same thing forever."""


def _extend_presets(children: st.SearchStrategy[Spec]) -> st.SearchStrategy[Spec]:
    return st.one_of(
        _extend(children),
        st.tuples(
            st.sampled_from(["MySequence", "MyFallback"]),
            st.lists(children, min_size=1, max_size=3),
        ),
        st.tuples(st.just("MyChoice"), st.lists(children, min_size=2, max_size=3)),
        st.tuples(
            st.sampled_from(
                [
                    "MyInverter",
                    "KeepTrying",
                    "WaitFor",
                    *(f"RepeatUntil until={{{f}}}" for f in FLAGS),
                    *(f"RepeatOrFail flag={{{f}}}" for f in FLAGS),
                ]
            ),
            children.map(lambda c: [c]),
        ),
    )


PRESET_TREES: st.SearchStrategy[Spec] = st.recursive(_LEAVES, _extend_presets, max_leaves=12)


def to_xml_presets(spec: Spec) -> str:
    if len(spec) == 1:
        return f"<{spec[0]}/>"
    head, children = spec[0], spec[1]
    name, _, port = head.partition(" ")
    attribute = f' {port.replace("=", "=" + chr(34))}"' if port else ""
    return f"<{name}{attribute}>{''.join(to_xml_presets(c) for c in children)}</{name}>"


@dataclass
class RunPresets(Run):
    """The reference interpreter, taught the presets."""

    def tick(self, node: Node) -> bool:
        if node.behaves_like is None or node.semantics in (
            Semantics.SEQUENCE,
            Semantics.FALLBACK,
            Semantics.IF_THEN_ELSE,
            Semantics.INVERTER,
        ):
            return super().tick(node)
        child = node.children[0]
        if node.semantics is Semantics.UNTIL_SUCCESS:
            if self.tick(child):
                return True
            raise Stuck  # the same failure, again and again
        assert node.semantics is Semantics.LOOP_UNTIL_FLAG
        flag = self.conditions[node.ports[node.options["flag_port"]].strip("{}")]
        exit_result = node.options["exit"] == "success"
        if flag:
            return exit_result
        if not self.tick(child):
            return False
        raise Stuck  # the flag is still not set: the child runs again


def follow_or_stuck(
    graph: ActionGraph, values: dict[str, bool], outcomes: Sequence[bool]
) -> tuple[list[int], bool | None]:
    index = {v.id: i for i, v in enumerate(graph.actions)}
    holds = {f"{c}()": values[c] for c in CONDITIONS} | {f: values[f] for f in FLAGS}
    trace: list[int] = []
    current = START
    while True:
        outcome = None
        if current != START:
            outcome = Outcome.SUCCESS if outcomes[index[current]] else Outcome.FAILURE
        matching = [
            e
            for e in graph.outgoing(current)
            if e.outcome == outcome
            and all(holds[lit.condition.key] == lit.positive for lit in e.guard)
        ]
        assert len(matching) <= 1, f"{len(matching)} edges match out of {current}"
        if not matching:
            return trace, None
        current = matching[0].target
        if current in (SUCCESS, FAILURE):
            return trace, current == SUCCESS
        assert len(trace) <= len(graph.actions), "the graph loops"
        trace.append(index[current])


@settings(max_examples=400, deadline=None)
@given(spec=PRESET_TREES, data=st.data())
def test_presets_agree_with_execution(spec: Spec, data: st.DataObject) -> None:
    xml = f'<root><BehaviorTree ID="T">{to_xml_presets(spec)}</BehaviorTree></root>'
    flat = flatten(parse_string(xml, config=PRESET_CONFIG))
    graph = build_graph(flat)

    values = {name: data.draw(st.booleans(), label=name) for name in (*CONDITIONS, *FLAGS)}
    outcomes = data.draw(
        st.lists(st.booleans(), min_size=len(graph.actions), max_size=len(graph.actions))
    )
    actions = [
        n for n in flat.root.walk() if n.kind is NodeKind.ACTION and n.semantics is Semantics.CUSTOM
    ]
    preorder = {id(n): i for i, n in enumerate(flat.root.walk())}
    run = RunPresets(values, outcomes, {id(n): i for i, n in enumerate(actions)}, preorder=preorder)
    try:
        result: bool | None = run.tick(flat.root)
    except Stuck:
        result = None

    assert follow_or_stuck(graph, values, outcomes) == (run.trace, result)
    # Every diagnostic is about a loop whose edges back to its child are missing.
    for diagnostic in graph.diagnostics:
        assert "the edges back to the child are not shown yet" in diagnostic.message


# ---------------------------------------------------- bookkeeping actions ---

# "Log" may fail and "Note" never does. Neither is a box: the graph, followed
# with the same results, must visit the other actions in the order the tree
# runs them (the run projected onto real actions), with one edge at each step.
BOOKKEEPING_CONFIG = config_from_dict(
    {
        "conditions": list(CONDITIONS),
        "bookkeeping": {"Log": {}, "Note": {"never_fails": True}},
    }
)
_LEAVES_BOOKKEEPING = st.sampled_from(
    [("Act",), ("Act",), ("Log",), ("Note",), *((c,) for c in CONDITIONS), ("AlwaysFailure",)]
)
BOOKKEEPING_TREES: st.SearchStrategy[Spec] = st.recursive(
    _LEAVES_BOOKKEEPING, _extend, max_leaves=14
)


@dataclass
class RunBookkeeping(Run):
    """The reference interpreter; bookkeeping results come from ``logged``."""

    logged: dict[int, bool] = field(default_factory=dict)

    def tick(self, node: Node) -> bool:
        if node.semantics is Semantics.BOOKKEEPING:
            return node.options["never_fails"] == "true" or self.logged[id(node)]
        return super().tick(node)


@settings(max_examples=400, deadline=None)
@given(spec=BOOKKEEPING_TREES, data=st.data())
def test_bookkeeping_is_collapsed_without_changing_what_runs(
    spec: Spec, data: st.DataObject
) -> None:
    xml = f'<root><BehaviorTree ID="T">{to_xml(spec)}</BehaviorTree></root>'
    flat = flatten(parse_string(xml, config=BOOKKEEPING_CONFIG))
    graph = build_graph(flat)

    # Every Log node gets its own result; its guard key is its type and tree path.
    paths: dict[int, str] = {}

    def visit(node: Node, at: tuple[int, ...]) -> None:
        paths[id(node)] = ".".join(map(str, at))
        for index, child in enumerate(node.children):
            visit(child, (*at, index))

    visit(flat.root, ())
    logs = [n for n in flat.root.walk() if n.type == "Log"]
    logged = {id(n): data.draw(st.booleans(), label=f"Log@{paths[id(n)]}") for n in logs}
    conditions = {c: data.draw(st.booleans(), label=c) for c in CONDITIONS}
    actions = [n for n in flat.root.walk() if n.type == "Act"]
    outcomes = data.draw(st.lists(st.booleans(), min_size=len(actions), max_size=len(actions)))
    assert len(graph.actions) == len(actions), "bookkeeping actions became boxes"

    run = RunBookkeeping(
        conditions,
        outcomes,
        {id(n): i for i, n in enumerate(actions)},
        preorder={id(n): i for i, n in enumerate(flat.root.walk())},
        logged=logged,
    )
    result = run.tick(flat.root)

    holds = {f"{name}()": value for name, value in conditions.items()}
    holds |= {f"Log@{paths[id(n)]}": logged[id(n)] for n in logs}
    index = {v.id: i for i, v in enumerate(graph.actions)}
    trace: list[int] = []
    current = START
    while current not in (SUCCESS, FAILURE):
        outcome = None
        if current != START:
            outcome = Outcome.SUCCESS if outcomes[index[current]] else Outcome.FAILURE
        matching = [
            e
            for e in graph.outgoing(current)
            if e.outcome == outcome
            and all(holds[lit.condition.key] == lit.positive for lit in e.guard)
        ]
        assert len(matching) == 1, f"{len(matching)} edges match out of {current}"
        current = matching[0].target
        if current not in (SUCCESS, FAILURE):
            trace.append(index[current])

    assert (trace, current == SUCCESS) == (run.trace, result)
