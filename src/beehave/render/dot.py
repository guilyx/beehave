"""Graphviz DOT rendering."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beehave.render import theme
from beehave.render._common import edge_label, header

if TYPE_CHECKING:
    from beehave.graph import ActionGraph, Vertex


def to_dot(graph: ActionGraph) -> str:
    """Render the graph as a Graphviz ``digraph``."""
    lines = [f"// {header(graph)}", f"digraph {quote(graph.tree)} {{"]
    lines += [f"  {line};" for line in theme.DOT_DEFAULTS]
    lines += [f"  {_vertex(v)};" for v in graph.vertices]
    for edge in graph.edges:
        attrs = []
        label = edge_label(edge)
        if label:
            attrs.append(f"label={quote(label)}")
        attrs.append(theme.DOT_EDGES[edge.outcome])
        lines.append(f"  {quote(edge.source)} -> {quote(edge.target)} [{', '.join(attrs)}];")
    lines.append("}")
    return "\n".join(lines) + "\n"


def quote(text: str) -> str:
    """Return ``text`` as a double-quoted DOT ID."""
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _vertex(vertex: Vertex) -> str:
    label = vertex.label
    if vertex.notes:
        label += "\n" + ", ".join(vertex.notes)
    attrs = [f"label={quote(label)}", theme.DOT_VERTICES[vertex.kind.value]]
    return f"{quote(vertex.id)} [{', '.join(attrs)}]"
