"""Helpers shared by the renderers."""

from __future__ import annotations

from collections import Counter
from typing import TYPE_CHECKING

from beehave.graph import VertexKind

if TYPE_CHECKING:
    from beehave.graph import ActionGraph, Edge


def edge_label(edge: Edge) -> str:
    """Return an edge's label: its outcome and guard, e.g. ``failure and not BatteryOK``."""
    parts = [edge.outcome.value] if edge.outcome else []
    parts += [str(literal) for literal in edge.guard]
    return " and ".join(parts)


def display_names(graph: ActionGraph) -> dict[str, str]:
    """Map vertex IDs to labels, suffixing ``#n`` when actions share a label."""
    counts = Counter(v.label for v in graph.vertices)
    seen: Counter[str] = Counter()
    names: dict[str, str] = {}
    for vertex in graph.vertices:
        if vertex.kind is VertexKind.ACTION and counts[vertex.label] > 1:
            seen[vertex.label] += 1
            names[vertex.id] = f"{vertex.label}#{seen[vertex.label]}"
        else:
            names[vertex.id] = vertex.label
    return names


def header(graph: ActionGraph) -> str:
    """A one-line description of the graph, for comments in the output."""
    return f"Beehave action graph: {graph.tree} ({graph.format})"
