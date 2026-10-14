"""The action graph: the output of the walk.

Vertices are actions plus three terminals (``START``, ``SUCCESS``, ``FAILURE``).
An edge says "when ``source`` ends with ``outcome`` and ``guard`` holds, the
next action is ``target``". Conditions never become vertices; they only appear
in guards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beehave.diagnostics import Diagnostic
    from beehave.model import SourceLocation


class VertexKind(str, Enum):
    """What a vertex stands for."""

    START = "start"
    ACTION = "action"
    SUCCESS = "success"
    FAILURE = "failure"


class Outcome(str, Enum):
    """How an action ended."""

    SUCCESS = "success"
    FAILURE = "failure"


START = "start"
SUCCESS = "success"
FAILURE = "failure"


@dataclass(frozen=True)
class Condition:
    """Something a guard can check.

    Attributes:
        key: Identity. Two checks with the same key always agree within a tick.
        label: How to show the condition when it holds.
        negated_label: How to show it when it does not hold, if not ``"not <label>"``.
    """

    key: str
    label: str
    negated_label: str | None = None


@dataclass(frozen=True)
class Literal:
    """A condition that must hold (``positive``) or must not hold."""

    condition: Condition
    positive: bool = True

    def negate(self) -> Literal:
        """Return the opposite literal."""
        return Literal(self.condition, not self.positive)

    def __str__(self) -> str:
        if self.positive:
            return self.condition.label
        return self.condition.negated_label or f"not {self.condition.label}"


Guard = tuple[Literal, ...]
"""A conjunction of literals. The empty guard always holds."""


@dataclass(frozen=True)
class Vertex:
    """A box in the action graph.

    Attributes:
        id: Stable identifier: ``start``, ``success``, ``failure``, or ``a1``, ``a2``…
            for actions in document order.
        kind: What the vertex stands for.
        label: The text to show.
        type: For actions, the node type (e.g. ``"GoToZone"``).
        ports: For actions, the port values after subtree remapping.
        notes: Short annotations such as ``"retry ×3"``.
        subtrees: For actions, the subtrees they were inlined from, outermost first.
        location: For actions, where the node was read from.
    """

    id: str
    kind: VertexKind
    label: str
    type: str | None = None
    ports: Mapping[str, str] = field(default_factory=dict)
    notes: tuple[str, ...] = ()
    subtrees: tuple[str, ...] = ()
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Edge:
    """A transition between two vertices.

    Attributes:
        source: The vertex the transition leaves.
        target: The vertex the transition reaches.
        outcome: How ``source`` ended; ``None`` for edges leaving ``START``.
        guard: What must hold for this transition to be taken.
    """

    source: str
    target: str
    outcome: Outcome | None
    guard: Guard = ()


@dataclass(frozen=True)
class ActionGraph:
    """The simplified view of a tree: actions and what runs next.

    Attributes:
        tree: The ID of the tree this graph was built from.
        format: The source format of that tree.
        vertices: ``START``, the actions in document order, then ``SUCCESS`` and ``FAILURE``.
        edges: Transitions, grouped by source vertex, success before failure.
        diagnostics: What the walk could not model exactly.
        node_count: How many nodes the flattened tree had (for the reduction metric).
    """

    tree: str
    format: str
    vertices: tuple[Vertex, ...]
    edges: tuple[Edge, ...]
    diagnostics: tuple[Diagnostic, ...] = ()
    node_count: int = 0

    def vertex(self, vertex_id: str) -> Vertex:
        """Return the vertex with this ID.

        Raises:
            KeyError: If there is no such vertex.
        """
        for vertex in self.vertices:
            if vertex.id == vertex_id:
                return vertex
        raise KeyError(vertex_id)

    @property
    def actions(self) -> tuple[Vertex, ...]:
        """The action vertices, in document order."""
        return tuple(v for v in self.vertices if v.kind is VertexKind.ACTION)

    def outgoing(self, vertex_id: str) -> tuple[Edge, ...]:
        """Return the edges leaving a vertex."""
        return tuple(e for e in self.edges if e.source == vertex_id)
