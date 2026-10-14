"""Mermaid flowchart rendering.

Success edges are solid, failure edges dashed, so the graph stays readable in
greyscale and for colour-blind readers; colour is only a second cue.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beehave.graph import Outcome, VertexKind
from beehave.render import theme
from beehave.render._common import edge_label, header

if TYPE_CHECKING:
    from beehave.graph import ActionGraph, Vertex

_SHAPES = {
    VertexKind.START: ("((", "))"),
    VertexKind.ACTION: ("[", "]"),
    VertexKind.SUCCESS: ("([", "])"),
    VertexKind.FAILURE: ("([", "])"),
}


def to_mermaid(graph: ActionGraph) -> str:
    """Render the graph as a Mermaid ``flowchart TD``."""
    lines = [f"%% {header(graph)}", "flowchart TD"]
    lines += [f"    {_vertex(v)}" for v in graph.vertices]
    for edge in graph.edges:
        arrow = "-.->" if edge.outcome is Outcome.FAILURE else "-->"
        label = edge_label(edge)
        text = f'|"{escape(label)}"|' if label else ""
        lines.append(f"    {edge.source} {arrow}{text} {edge.target}")
    lines += _styles(graph)
    return "\n".join(lines) + "\n"


def escape(text: str) -> str:
    """Escape text for a quoted Mermaid label using Mermaid entity codes."""
    text = text.replace("#", "#35;")
    for char, code in (('"', "#quot;"), ("<", "#lt;"), (">", "#gt;")):
        text = text.replace(char, code)
    return text


def _vertex(vertex: Vertex) -> str:
    left, right = _SHAPES[vertex.kind]
    label = escape(vertex.label)
    if vertex.notes:
        label += "<br/><small>" + escape(", ".join(vertex.notes)) + "</small>"
    return f'{vertex.id}{left}"{label}"{right}'


def _styles(graph: ActionGraph) -> list[str]:
    lines = [f"    classDef {name} {style}" for name, style in theme.MERMAID_CLASSES.items()]
    groups: dict[str, list[str]] = {}
    for vertex in graph.vertices:
        groups.setdefault(vertex.kind.value, []).append(vertex.id)
    lines += [f"    class {','.join(ids)} {kind}" for kind, ids in groups.items()]
    failure_edges = [str(i) for i, e in enumerate(graph.edges) if e.outcome is Outcome.FAILURE]
    if failure_edges:
        lines.append(f"    linkStyle {','.join(failure_edges)} {theme.MERMAID_FAILURE_EDGE}")
    return lines
