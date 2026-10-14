"""Default visual style for rendered graphs.

The values come from the brand palette in ``.branding/``. Shape and line style
always carry the meaning (dashed = failure, stadium = terminal), so the graph
still reads in greyscale; colour is a second cue.
"""

from __future__ import annotations

# Placeholder neutral palette; replaced by the brand tokens.
MERMAID_CLASSES = {
    "start": "fill:#222222,stroke:#222222,color:#ffffff",
    "action": "fill:#ffffff,stroke:#222222,color:#222222",
    "success": "fill:#ffffff,stroke:#222222,color:#222222",
    "failure": "fill:#ffffff,stroke:#222222,color:#222222,stroke-dasharray:4 3",
}
MERMAID_FAILURE_EDGE = "stroke-dasharray:5 4"

DOT_DEFAULTS = (
    'graph [rankdir=TB, fontname="Helvetica"]',
    'node [shape=box, style="rounded", fontname="Helvetica"]',
    'edge [fontname="Helvetica", fontsize=10]',
)
DOT_VERTICES = {
    "start": "shape=circle",
    "action": "shape=box",
    "success": 'shape=box, style="rounded,bold"',
    "failure": 'shape=box, style="rounded,dashed"',
}
DOT_FAILURE_EDGE = "style=dashed"
