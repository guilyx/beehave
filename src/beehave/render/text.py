"""Plain-text rendering: one transition per line."""

from __future__ import annotations

from typing import TYPE_CHECKING

from beehave.render._common import display_names, edge_label

if TYPE_CHECKING:
    from beehave.graph import ActionGraph


def to_text(graph: ActionGraph) -> str:
    """Render the graph as ``SOURCE --[label]--> TARGET`` lines.

    Actions that share a label get a ``#n`` suffix. Notes such as
    ``retry ×3`` are listed after the transitions.
    """
    names = display_names(graph)
    lines = []
    for edge in graph.edges:
        label = edge_label(edge)
        arrow = f"--[{label}]-->" if label else "-->"
        lines.append(f"{names[edge.source]} {arrow} {names[edge.target]}")
    notes = [(names[v.id], note) for v in graph.actions for note in v.notes]
    if notes:
        lines += ["", "notes:"] + [f"  {name}: {note}" for name, note in notes]
    return "\n".join(lines) + "\n"
