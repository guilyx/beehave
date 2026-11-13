"""Diff: what changed between the action graphs of two trees.

Two versions of a tree rarely number their actions the same way: one action
added near the top shifts every display ID (``a1``, ``a2``…) and every runtime
id after it. So the diff matches vertices by their stable path
(:attr:`beehave.NodeRef.path`), and guard terms by their condition key, never
by numbers. Renaming a node, or moving it, changes its path. An action whose
path is the only thing that changed is reported as moved when the pairing is
unambiguous (one action gone and one new, with the same content); otherwise it
shows as one action removed and one added.

What it reports:

- actions added, removed, moved, or changed (label, type, ports, notes, subtrees);
- transitions added and removed, and transitions kept whose guards changed;
- vertices that became reachable or unreachable from ``START``, ends included;
- a transition score: precision, recall and F1 of the new graph's
  transitions against the old one's, guards left out.

Everything is computed from the two graphs alone.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from beehave.graph import START, VertexKind
from beehave.hashing import graph_hash

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping

    from beehave.graph import ActionGraph, Edge, Vertex

_TERMINALS = {
    VertexKind.START: "START",
    VertexKind.SUCCESS: "SUCCESS",
    VertexKind.FAILURE: "FAILURE",
    VertexKind.SKIPPED: "SKIPPED",
}
_FIELDS = ("label", "type", "ports", "notes", "subtrees")
_OUTCOMES = {None: 0, "success": 1, "failure": 2}


@dataclass(frozen=True, order=True)
class VertexKey:
    """How a vertex is matched across two graphs.

    Attributes:
        terminal: ``START``, ``SUCCESS``, ``FAILURE`` or ``SKIPPED``; empty for an action.
        path: For an action, the stable path of its node.
    """

    terminal: str = ""
    path: str = ""

    def __str__(self) -> str:
        return self.terminal or self.path


@dataclass(frozen=True, order=True)
class Term:
    """One term of a guard: a condition that must hold, or must not.

    Attributes:
        key: The condition's identity (see :class:`beehave.graph.Condition`).
        holds: Whether it must hold.
        text: How the term reads, e.g. ``"not IsBatteryOK"``.
    """

    key: str
    holds: bool
    text: str = field(compare=False)


@dataclass(frozen=True, order=True)
class Transition:
    """A transition, as the diff sees it: endpoints by key, the guard as terms.

    Attributes:
        source: Where it leaves from.
        outcome: ``"success"``, ``"failure"``, or ``None`` from ``START``.
        target: Where it goes.
        guard: The terms that must hold, sorted by key.
    """

    source: VertexKey
    outcome: str | None
    target: VertexKey
    guard: tuple[Term, ...] = ()

    @property
    def step(self) -> tuple[VertexKey, str | None, VertexKey]:
        """The transition without its guard."""
        return (self.source, self.outcome, self.target)


@dataclass(frozen=True)
class ActionChange:
    """An action present in both graphs whose content changed.

    Attributes:
        key: The action.
        changes: Each changed field (``label``, ``type``, ``ports``, ``notes``,
            ``subtrees``), with its old and new value.
    """

    key: VertexKey
    changes: Mapping[str, tuple[Any, Any]]


@dataclass(frozen=True)
class GuardChange:
    """A step kept in both graphs whose guards changed.

    Attributes:
        source: Where it leaves from.
        outcome: How the source ended.
        target: Where it goes.
        removed: Guards only the old graph has on this step.
        added: Guards only the new graph has on this step.
    """

    source: VertexKey
    outcome: str | None
    target: VertexKey
    removed: tuple[tuple[Term, ...], ...]
    added: tuple[tuple[Term, ...], ...]


@dataclass(frozen=True)
class TransitionScore:
    """How well the new graph's transitions match the old one's, guards left out.

    The old graph is the reference: precision is the share of new transitions
    the old graph has, recall the share of old transitions the new graph keeps.
    Both are 1 when there is nothing to compare.

    Attributes:
        matched: Transitions in both graphs.
        old: Transitions in the old graph.
        new: Transitions in the new graph.
    """

    matched: int
    old: int
    new: int

    @property
    def precision(self) -> float:
        """``matched / new``."""
        return self.matched / self.new if self.new else 1.0

    @property
    def recall(self) -> float:
        """``matched / old``."""
        return self.matched / self.old if self.old else 1.0

    @property
    def f1(self) -> float:
        """The harmonic mean of precision and recall."""
        total = self.precision + self.recall
        return 2 * self.precision * self.recall / total if total else 0.0


@dataclass(frozen=True)
class GraphDiff:
    """What changed from one action graph to another.

    Attributes:
        old_tree: The old graph's tree ID.
        new_tree: The new graph's tree ID.
        old_hash: The old graph's hash (:func:`beehave.graph_hash`).
        new_hash: The new graph's hash.
        moved_actions: Actions whose path changed but nothing else, as
            ``(old path, new path)``. Everything else in the diff names them by
            their new path. A move alone is not a change of the graph.
        added_actions: Actions only the new graph has.
        removed_actions: Actions only the old graph has.
        changed_actions: Actions in both whose content changed.
        added_transitions: Transitions only the new graph has, except those
            listed in ``changed_guards``.
        removed_transitions: Transitions only the old graph has, except those
            listed in ``changed_guards``.
        changed_guards: Steps in both graphs whose guards changed.
        became_reachable: Vertices in both graphs that only the new graph reaches.
        became_unreachable: Vertices in both graphs that only the old graph reaches.
        score: The transition score.
        labels: How to show each vertex key: its label in the new graph, else
            in the old one.
    """

    old_tree: str
    new_tree: str
    old_hash: str
    new_hash: str
    moved_actions: tuple[tuple[VertexKey, VertexKey], ...]
    added_actions: tuple[VertexKey, ...]
    removed_actions: tuple[VertexKey, ...]
    changed_actions: tuple[ActionChange, ...]
    added_transitions: tuple[Transition, ...]
    removed_transitions: tuple[Transition, ...]
    changed_guards: tuple[GuardChange, ...]
    became_reachable: tuple[VertexKey, ...]
    became_unreachable: tuple[VertexKey, ...]
    score: TransitionScore
    labels: Mapping[VertexKey, str] = field(default_factory=dict, compare=False)

    @property
    def changed(self) -> bool:
        """Whether any action, transition, guard or reachability changed."""
        return any(
            (
                self.added_actions,
                self.removed_actions,
                self.changed_actions,
                self.added_transitions,
                self.removed_transitions,
                self.changed_guards,
                self.became_reachable,
                self.became_unreachable,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the diff as JSON data (schema ``beehave.graph-diff``, version 1)."""
        return {
            "schema": "beehave.graph-diff",
            "version": 1,
            "old": {"tree": self.old_tree, "graph_hash": self.old_hash},
            "new": {"tree": self.new_tree, "graph_hash": self.new_hash},
            "changed": self.changed,
            "actions": {
                "moved": [
                    {"from": self._vertex(a), "to": self._vertex(b)} for a, b in self.moved_actions
                ],
                "added": [self._vertex(k) for k in self.added_actions],
                "removed": [self._vertex(k) for k in self.removed_actions],
                "changed": [
                    {
                        **self._vertex(c.key),
                        "changes": {
                            name: {"old": _plain(old), "new": _plain(new)}
                            for name, (old, new) in c.changes.items()
                        },
                    }
                    for c in self.changed_actions
                ],
            },
            "transitions": {
                "added": [self._transition(t) for t in self.added_transitions],
                "removed": [self._transition(t) for t in self.removed_transitions],
                "changed_guards": [
                    {
                        "from": self._vertex(c.source),
                        "outcome": c.outcome,
                        "to": self._vertex(c.target),
                        "removed": [_guard(g) for g in c.removed],
                        "added": [_guard(g) for g in c.added],
                    }
                    for c in self.changed_guards
                ],
            },
            "reachability": {
                "became_reachable": [self._vertex(k) for k in self.became_reachable],
                "became_unreachable": [self._vertex(k) for k in self.became_unreachable],
            },
            "score": {
                "matched": self.score.matched,
                "old": self.score.old,
                "new": self.score.new,
                "precision": round(self.score.precision, 4),
                "recall": round(self.score.recall, 4),
                "f1": round(self.score.f1, 4),
            },
        }

    def to_json(self) -> str:
        """Render the diff as a JSON document."""
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    def to_text(self) -> str:
        """Render the diff as plain text, one change per line."""
        moves = [f"> action {a} moved to {b}" for a, b in self.moved_actions]
        if not self.changed:
            return "\n".join([*moves, "no change"]) + "\n"
        lines: list[str] = moves
        for sign, keys in (("+", self.added_actions), ("-", self.removed_actions)):
            lines += [f"{sign} action {self._name(k)}" for k in keys]
        for change in self.changed_actions:
            for name, (old, new) in change.changes.items():
                lines.append(
                    f"~ action {self._name(change.key)}: {name} {_show(old)} -> {_show(new)}"
                )
        for sign, transitions in (
            ("+", self.added_transitions),
            ("-", self.removed_transitions),
        ):
            lines += [f"{sign} {self._arrow(t)}" for t in transitions]
        for guards in self.changed_guards:
            step = Transition(guards.source, guards.outcome, guards.target)
            lines += [f"~ {self._arrow(step)}: guard - [{_text(g)}]" for g in guards.removed]
            lines += [f"~ {self._arrow(step)}: guard + [{_text(g)}]" for g in guards.added]
        lines += [f"! {self._name(k)} became reachable" for k in self.became_reachable]
        lines += [f"! {self._name(k)} became unreachable" for k in self.became_unreachable]
        score = self.score
        lines.append(
            f"transitions: {score.matched} of {score.old} kept, {score.new} now; "
            f"precision {score.precision:.2f}, recall {score.recall:.2f}, F1 {score.f1:.2f}"
        )
        return "\n".join(lines) + "\n"

    def to_markdown(self) -> str:
        """Render the diff as Markdown, for a pull-request comment."""
        title = f"### Action graph diff: `{self.old_tree}` → `{self.new_tree}`\n\n"
        moved = "".join(f"- `{a}` → `{b}`\n" for a, b in self.moved_actions)
        moved = f"\n**Actions moved** (path changed only)\n\n{moved}" if moved else ""
        if not self.changed:
            return title + "No change to the action graph.\n" + moved
        score = self.score
        out = [
            title,
            "| | Added | Removed | Changed |\n| --- | --- | --- | --- |\n",
            (
                f"| Actions | {len(self.added_actions)} | {len(self.removed_actions)} "
                f"| {len(self.changed_actions)} |\n"
            ),
            (
                f"| Transitions | {len(self.added_transitions)} "
                f"| {len(self.removed_transitions)} | {len(self.changed_guards)} guards |\n\n"
            ),
            (
                f"Transitions kept: {score.matched} of {score.old} (precision "
                f"{score.precision:.2f}, recall {score.recall:.2f}, F1 {score.f1:.2f}).\n"
            ),
        ]
        sections = [
            ("Actions added", [f"`{self._name(k)}`" for k in self.added_actions]),
            ("Actions removed", [f"`{self._name(k)}`" for k in self.removed_actions]),
            (
                "Actions changed",
                [
                    f"`{self._name(c.key)}`: {name} `{_show(old)}` → `{_show(new)}`"
                    for c in self.changed_actions
                    for name, (old, new) in c.changes.items()
                ],
            ),
            ("Transitions added", [f"`{self._arrow(t)}`" for t in self.added_transitions]),
            ("Transitions removed", [f"`{self._arrow(t)}`" for t in self.removed_transitions]),
            (
                "Guards changed",
                [
                    f"`{self._arrow(Transition(g.source, g.outcome, g.target))}`: "
                    + ", ".join(
                        [f"removed `[{_text(old)}]`" for old in g.removed]
                        + [f"added `[{_text(new)}]`" for new in g.added]
                    )
                    for g in self.changed_guards
                ],
            ),
            (
                "Reachability",
                [f"`{self._name(k)}` became reachable" for k in self.became_reachable]
                + [f"`{self._name(k)}` became unreachable" for k in self.became_unreachable],
            ),
        ]
        for heading, items in sections:
            if items:
                out.append(f"\n**{heading}**\n\n" + "".join(f"- {item}\n" for item in items))
        return "".join(out) + moved

    def _name(self, key: VertexKey) -> str:
        # The path ends with the node's name or type, and tells actions apart.
        return str(key)

    def _arrow(self, transition: Transition) -> str:
        parts = [transition.outcome] if transition.outcome else []
        if transition.guard:
            parts.append(_text(transition.guard))
        label = f"--[{' and '.join(parts)}]-->" if parts else "-->"
        return f"{self._name(transition.source)} {label} {self._name(transition.target)}"

    def _vertex(self, key: VertexKey) -> dict[str, Any]:
        if key.terminal:
            return {"terminal": key.terminal}
        return {"path": key.path, "label": self.labels.get(key, key.path)}

    def _transition(self, transition: Transition) -> dict[str, Any]:
        return {
            "from": self._vertex(transition.source),
            "outcome": transition.outcome,
            "to": self._vertex(transition.target),
            "guard": _guard(transition.guard),
        }


def diff_graphs(old: ActionGraph, new: ActionGraph) -> GraphDiff:
    """Compare two action graphs, matching vertices by stable path.

    Args:
        old: The reference graph, e.g. from the base branch.
        new: The graph to compare with it.

    Returns:
        What changed, and the transition score of ``new`` against ``old``.

    Example:
        >>> import beehave
        >>> before = beehave.analyze("old/mission.xml").graph  # doctest: +SKIP
        >>> after = beehave.analyze("mission.xml").graph  # doctest: +SKIP
        >>> print(beehave.diff_graphs(before, after).to_text())  # doctest: +SKIP
    """
    old_vertices, new_vertices = _vertices(old), _vertices(new)
    moved = _moves(old_vertices, new_vertices)
    labels = {k: v.label for k, v in old_vertices.items()}
    labels.update({k: v.label for k, v in new_vertices.items()})
    # From here on, a moved action goes by its new path in both graphs.
    old_vertices = {moved.get(k, k): v for k, v in old_vertices.items()}
    old_actions = {k for k in old_vertices if not k.terminal}
    new_actions = {k for k in new_vertices if not k.terminal}

    changed_actions = []
    for key in sorted(old_actions & new_actions):
        a, b = old_vertices[key], new_vertices[key]
        changes = {
            name: (_value(a, name), _value(b, name))
            for name in _FIELDS
            if _value(a, name) != _value(b, name)
        }
        if changes:
            changed_actions.append(ActionChange(key, changes))

    old_transitions = _transitions(old, old_vertices)
    new_transitions = _transitions(new, new_vertices)
    added = new_transitions - old_transitions
    removed = old_transitions - new_transitions
    old_guards = _guards_by_step(removed)
    new_guards = _guards_by_step(added)
    changed_steps = old_guards.keys() & new_guards.keys()
    changed_guards = tuple(
        GuardChange(
            *step,
            removed=tuple(sorted(old_guards[step])),
            added=tuple(sorted(new_guards[step])),
        )
        for step in sorted(changed_steps, key=_step_order)
    )

    old_steps = {t.step for t in old_transitions}
    new_steps = {t.step for t in new_transitions}
    old_reached = _reachable(old_transitions)
    new_reached = _reachable(new_transitions)
    shared = old_vertices.keys() & new_vertices.keys()

    return GraphDiff(
        old_tree=old.tree,
        new_tree=new.tree,
        old_hash=graph_hash(old),
        new_hash=graph_hash(new),
        moved_actions=tuple(sorted(moved.items())),
        added_actions=tuple(sorted(new_actions - old_actions)),
        removed_actions=tuple(sorted(old_actions - new_actions)),
        changed_actions=tuple(changed_actions),
        added_transitions=_sorted(t for t in added if t.step not in changed_steps),
        removed_transitions=_sorted(t for t in removed if t.step not in changed_steps),
        changed_guards=changed_guards,
        became_reachable=tuple(sorted((new_reached - old_reached) & shared)),
        became_unreachable=tuple(sorted((old_reached - new_reached) & shared)),
        score=TransitionScore(len(old_steps & new_steps), len(old_steps), len(new_steps)),
        labels=labels,
    )


def _moves(
    old: Mapping[VertexKey, Vertex], new: Mapping[VertexKey, Vertex]
) -> dict[VertexKey, VertexKey]:
    """Pair actions that only changed path, when the pairing is unambiguous.

    An action whose path is gone and an action whose path is new are the same
    action moved if they have the same content (label, type, ports, notes,
    subtrees) and no other gone or new action has that content.
    """
    gone: dict[tuple[Any, ...], list[VertexKey]] = defaultdict(list)
    came: dict[tuple[Any, ...], list[VertexKey]] = defaultdict(list)
    for key, vertex in old.items():
        if not key.terminal and key not in new:
            gone[_content(vertex)].append(key)
    for key, vertex in new.items():
        if not key.terminal and key not in old:
            came[_content(vertex)].append(key)
    return {
        keys[0]: came[content][0]
        for content, keys in gone.items()
        if len(keys) == 1 and len(came.get(content, ())) == 1
    }


def _content(vertex: Vertex) -> tuple[Any, ...]:
    return (
        vertex.label,
        vertex.type,
        tuple(sorted(vertex.ports.items())),
        vertex.notes,
        vertex.subtrees,
    )


def _vertices(graph: ActionGraph) -> dict[VertexKey, Vertex]:
    vertices: dict[VertexKey, Vertex] = {}
    for vertex in graph.vertices:
        if vertex.kind in _TERMINALS:
            vertices[VertexKey(terminal=_TERMINALS[vertex.kind])] = vertex
        else:
            # Every action records its node; the display ID is a last resort.
            path = vertex.node.path if vertex.node else f"#{vertex.id}"
            vertices[VertexKey(path=path)] = vertex
    return vertices


def _transitions(graph: ActionGraph, vertices: Mapping[VertexKey, Vertex]) -> set[Transition]:
    by_id = {vertex.id: key for key, vertex in vertices.items()}
    return {_transition(edge, by_id) for edge in graph.edges}


def _transition(edge: Edge, by_id: Mapping[str, VertexKey]) -> Transition:
    terms = sorted(Term(lit.condition.key, lit.positive, str(lit)) for lit in edge.guard)
    return Transition(
        by_id[edge.source],
        edge.outcome.value if edge.outcome else None,
        by_id[edge.target],
        tuple(terms),
    )


def _guards_by_step(
    transitions: Iterable[Transition],
) -> dict[tuple[VertexKey, str | None, VertexKey], set[tuple[Term, ...]]]:
    guards: dict[tuple[VertexKey, str | None, VertexKey], set[tuple[Term, ...]]] = defaultdict(set)
    for transition in transitions:
        guards[transition.step].add(transition.guard)
    return guards


def _reachable(transitions: Iterable[Transition]) -> set[VertexKey]:
    successors: dict[VertexKey, set[VertexKey]] = defaultdict(set)
    for transition in transitions:
        successors[transition.source].add(transition.target)
    start = VertexKey(terminal=_TERMINALS[VertexKind.START])
    seen = {start}
    stack = [start]
    while stack:
        for nxt in successors[stack.pop()] - seen:
            seen.add(nxt)
            stack.append(nxt)
    return seen


def _value(vertex: Vertex, name: str) -> Any:
    value = getattr(vertex, name)
    return dict(value) if name == "ports" else value


def _sorted(transitions: Iterable[Transition]) -> tuple[Transition, ...]:
    return tuple(sorted(transitions, key=lambda t: (_step_order(t.step), t.guard)))


def _step_order(step: tuple[VertexKey, str | None, VertexKey]) -> tuple[Any, ...]:
    source, outcome, target = step
    # START first, then actions by path; success before failure.
    return (source.terminal != START.upper(), source, _OUTCOMES[outcome], target)


def _guard(guard: tuple[Term, ...]) -> list[dict[str, Any]]:
    return [{"condition": t.text, "key": t.key, "holds": t.holds} for t in guard]


def _text(guard: tuple[Term, ...]) -> str:
    return " and ".join(t.text for t in guard) or "no guard"


def _plain(value: Any) -> Any:
    return list(value) if isinstance(value, tuple) else value


def _show(value: Any) -> str:
    if isinstance(value, dict):
        return "{" + ", ".join(f"{k}={v}" for k, v in sorted(value.items())) + "}"
    if isinstance(value, tuple):
        return "[" + ", ".join(map(str, value)) + "]"
    return str(value)


__all__ = [
    "ActionChange",
    "GraphDiff",
    "GuardChange",
    "Term",
    "Transition",
    "TransitionScore",
    "VertexKey",
    "diff_graphs",
]
