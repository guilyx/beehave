"""Pilot metrics for one tree.

These are the Phase 1 numbers from the design plan: how much smaller the graph
is than the tree (size, reduction), how long the raw guards get, and which
nodes Phase 1 could only approximate (breakage).
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any

from beehave.model import NodeKind

if TYPE_CHECKING:
    from collections.abc import Mapping

    from beehave.flatten import FlatTree
    from beehave.graph import ActionGraph

_BREAKAGE_CODES = frozenset({"approximated", "unknown-control", "unknown-decorator"})


@dataclass(frozen=True)
class Stats:
    """Size and coverage numbers for one tree.

    Attributes:
        tree: The tree ID.
        format: The source format.
        nodes: Nodes in the flattened tree (subtree references included).
        nodes_by_kind: The same count, per node kind.
        actions: Actions shown in the graph.
        transitions: Edges in the graph.
        reduction: ``1 - actions / nodes``: how much smaller the view is.
        longest_guard: Literals in the longest guard, before any simplification.
        approximated: Node types Phase 1 could not model exactly, with counts.
    """

    tree: str
    format: str
    nodes: int
    nodes_by_kind: Mapping[str, int]
    actions: int
    transitions: int
    reduction: float
    longest_guard: int
    approximated: Mapping[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return the metrics as plain data (for JSON)."""
        data = asdict(self)
        data["nodes_by_kind"] = dict(self.nodes_by_kind)
        data["approximated"] = dict(self.approximated)
        return data

    def to_text(self) -> str:
        """Return the metrics as an aligned, human-readable table."""
        kinds = ", ".join(f"{n} {k}" for k, n in self.nodes_by_kind.items() if n)
        approximated = ", ".join(f"{t} ×{n}" for t, n in self.approximated.items()) or "none"
        rows = [
            ("tree", f"{self.tree} ({self.format})"),
            ("nodes", f"{self.nodes} ({kinds})"),
            ("actions", str(self.actions)),
            ("reduction", f"{self.reduction:.0%} ({self.nodes} nodes -> {self.actions} actions)"),
            ("transitions", str(self.transitions)),
            ("longest guard", f"{self.longest_guard} terms (not simplified)"),
            ("approximated", approximated),
        ]
        return "".join(f"{name:<14} {value}\n" for name, value in rows)


def compute_stats(tree: FlatTree, graph: ActionGraph) -> Stats:
    """Compute the pilot metrics for a flattened tree and its graph."""
    kinds = Counter(node.kind.value for node in tree.root.walk())
    nodes = sum(kinds.values())
    actions = len(graph.actions)
    breakage = Counter(
        d.node_type for d in graph.diagnostics if d.code in _BREAKAGE_CODES and d.node_type
    )
    return Stats(
        tree=graph.tree,
        format=graph.format,
        nodes=nodes,
        nodes_by_kind={kind.value: kinds.get(kind.value, 0) for kind in NodeKind},
        actions=actions,
        transitions=len(graph.edges),
        reduction=1 - actions / nodes if nodes else 0.0,
        longest_guard=max((len(e.guard) for e in graph.edges), default=0),
        approximated=dict(sorted(breakage.items())),
    )
