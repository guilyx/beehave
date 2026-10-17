"""Renderers turn an :class:`~beehave.graph.ActionGraph` into text.

- :func:`to_text`: one line per transition, for terminals and code review.
- :func:`to_mermaid`: a Mermaid flowchart, renders on GitHub and in docs.
- :func:`to_dot`: Graphviz DOT, for large graphs and image export.
- :func:`to_json`: a stable, versioned document for other tools (and the C2 view).

Every renderer is deterministic: the same graph always gives the same bytes, so
outputs can be committed and diffed.
"""

from __future__ import annotations

from beehave.render.dot import to_dot
from beehave.render.json import to_json
from beehave.render.mermaid import to_mermaid
from beehave.render.text import to_text

FORMATS = {"text": to_text, "mermaid": to_mermaid, "dot": to_dot, "json": to_json}

__all__ = ["FORMATS", "to_dot", "to_json", "to_mermaid", "to_text"]
