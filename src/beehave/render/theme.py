"""Default visual style for rendered graphs.

The colours and fonts come from the brand tokens in ``.branding/tokens/``
(light theme). Shape and line style always carry the meaning on their own
(dashed = failure, stadium = terminal, dashed outline = skipped), so a graph
still reads in greyscale,
on a low-quality display or for colour-blind readers. Colour is a second cue.
"""

from __future__ import annotations

from beehave.graph import Outcome

# Brand tokens, light theme.
INK = "#1b1813"  # comb 21: text, START, transitions out of START
PAPER = "#fdfbf9"  # comb 99: action boxes
PAPER_TEXT = "#f5f0e9"  # comb 96: text on ink
MUTED = "#4b4740"  # comb 40: edge labels
LEAF = "#107550"  # leaf 50: success
CINNABAR = "#b93917"  # cinnabar 53: failure

SANS = "Archivo"
MONO = "Martian Mono"

# Mermaid reads this front matter, so labels sit on brand paper in any viewer.
# No font is set: viewers rarely have the brand fonts, and Mermaid clips labels
# when the font it measures with is not the one it draws with.
MERMAID_FRONTMATTER = (
    "---",
    "config:",
    "  theme: base",
    "  themeVariables:",
    f'    edgeLabelBackground: "{PAPER_TEXT}"',
    f'    lineColor: "{INK}"',
    "---",
)
MERMAID_CLASSES = {
    "start": f"fill:{INK},stroke:{INK},stroke-width:1.5px,color:{PAPER_TEXT}",
    "action": f"fill:{PAPER},stroke:{INK},stroke-width:1.5px,color:{INK}",
    # A paper-coloured stroke draws the terminal's inner ring.
    "success": f"fill:{LEAF},stroke:{PAPER},stroke-width:2px,color:{PAPER}",
    "failure": f"fill:{CINNABAR},stroke:{PAPER},stroke-width:2px,color:{PAPER}",
    # Only drawn for BT.CPP v4 trees that can skip; "not run" reads as muted.
    "skipped": (f"fill:{PAPER},stroke:{MUTED},stroke-width:2px,stroke-dasharray:4 3,color:{MUTED}"),
}
MERMAID_EDGES: dict[Outcome | None, str] = {
    None: f"stroke:{INK},stroke-width:1.75px",
    Outcome.SUCCESS: f"stroke:{LEAF},stroke-width:1.75px",
    Outcome.FAILURE: f"stroke:{CINNABAR},stroke-width:1.75px,stroke-dasharray:7 4",
}

DOT_DEFAULTS = (
    f'graph [rankdir=TB, fontname="{MONO}", fontsize=12, fontcolor="{MUTED}"]',
    (
        f'node [shape=box, style="rounded,filled", fillcolor="{PAPER}", color="{INK}", '
        f'penwidth=1.5, fontname="{SANS}", fontsize=14, fontcolor="{INK}"]'
    ),
    f'edge [penwidth=1.5, arrowsize=0.8, fontname="{MONO}", fontsize=11, fontcolor="{MUTED}"]',
)
DOT_VERTICES = {
    "start": f'shape=circle, fillcolor="{INK}", color="{INK}", fontcolor="{PAPER_TEXT}"',
    "action": "shape=box",
    "success": f'shape=doublecircle, fillcolor="{LEAF}", color="{LEAF}", fontcolor="{PAPER}"',
    "failure": (
        f'shape=doubleoctagon, fillcolor="{CINNABAR}", color="{CINNABAR}", fontcolor="{PAPER}"'
    ),
    "skipped": (
        f'shape=doublecircle, style="filled,dashed", fillcolor="{PAPER}", color="{MUTED}", '
        f'fontcolor="{MUTED}"'
    ),
}
DOT_EDGES: dict[Outcome | None, str] = {
    None: f'color="{INK}"',
    Outcome.SUCCESS: f'color="{LEAF}"',
    Outcome.FAILURE: f'color="{CINNABAR}", style=dashed',
}
