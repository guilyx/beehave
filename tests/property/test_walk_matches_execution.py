"""The action graph must agree with actually running the tree.

Hypothesis generates random trees made of the node types Phase 1 models
exactly, plus random values for every condition and random outcomes for every
action. A small reference interpreter runs the tree; following the action graph
with the same values must visit the same actions, in the same order, and end
with the same result. At every step exactly one outgoing edge must match, so
the guards are both complete and mutually exclusive.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, TypeAlias

from hypothesis import given, settings
from hypothesis import strategies as st

from beehave.config import Config
from beehave.flatten import flatten
from beehave.graph import FAILURE, START, SUCCESS, ActionGraph, Outcome
from beehave.model import Node, NodeKind, Semantics
from beehave.parsers import parse_string
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

    def tick(self, node: Node) -> bool:
        sem = node.semantics
        if node.kind is NodeKind.CONDITION:
            return self.conditions[node.type]
        if node.kind is NodeKind.ACTION:
            if sem is Semantics.ALWAYS_SUCCESS:
                return True
            if sem is Semantics.ALWAYS_FAILURE:
                return False
            index = self.action_index[id(node)]
            self.trace.append(index)
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
    run = Run(conditions, outcomes, {id(n): i for i, n in enumerate(actions)})
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
