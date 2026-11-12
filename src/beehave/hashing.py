"""Content hashes: name the tree and the graph a review, a robot and a log mean.

Two hashes, both SHA-256 over a canonical form, both computed from the tree
alone:

- :func:`tree_hash` hashes the **inlined tree** (:func:`canonical_xml`): the
  selected tree with every subtree inlined, written as XML with no whitespace,
  no comments, and attributes sorted. Layout, attribute order, comments and the
  file the tree came from do not change it; a node, a port, a name or the
  nesting does.
- :func:`graph_hash` hashes the **action graph**: its actions, their ports and
  notes, and every edge with its outcome and guard. Two trees with the same
  graph have the same graph hash, even when their XML differs (a BT.CPP v3
  tree and its v4 version, say). Diagnostics, source locations and node ids
  are left out.

The graph depends on Beehave's walk rules and on the project config, so
compare graph hashes made by the same Beehave version and config. The tree
hash depends on the tree only. Each hash starts with ``sha256:``; the
canonical forms are versioned, and a change to them is listed in the changelog.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape

from beehave.model import NodeKind

if TYPE_CHECKING:
    from beehave.flatten import FlatTree
    from beehave.graph import ActionGraph
    from beehave.model import Node

GRAPH_HASH_VERSION = 1
"""The version of the canonical form :func:`graph_hash` hashes."""
TREE_HASH_VERSION = 1
"""The version of the canonical form :func:`tree_hash` hashes."""

_ATTRIBUTE_ENTITIES = {'"': "&quot;", "\n": "&#10;", "\r": "&#13;", "\t": "&#9;"}
_XML_NAME = re.compile(r"[A-Za-z_][\w.\-]*")


def graph_hash(graph: ActionGraph) -> str:
    """Return the content hash of an action graph, e.g. ``"sha256:3f…"``.

    It covers the actions (id, label, type, ports, notes, subtrees) and the
    edges (source, target, outcome, and each guard term's key and polarity),
    not the tree ID, the source format, the diagnostics, source locations or
    node ids.
    """
    canonical = {
        "beehave-graph": GRAPH_HASH_VERSION,
        "vertices": [
            {
                "id": v.id,
                "kind": v.kind.value,
                "label": v.label,
                "type": v.type,
                "ports": dict(v.ports),
                "notes": list(v.notes),
                "subtrees": list(v.subtrees),
            }
            for v in graph.vertices
        ],
        "edges": [
            [
                e.source,
                e.target,
                e.outcome.value if e.outcome else None,
                [[lit.condition.key, lit.positive] for lit in e.guard],
            ]
            for e in graph.edges
        ],
    }
    return _sha256(json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False))


def tree_hash(flat: FlatTree) -> str:
    """Return the content hash of a flattened tree's :func:`canonical_xml`."""
    return _sha256(canonical_xml(flat))


def canonical_xml(flat: FlatTree) -> str:
    """Write a flattened tree as canonical XML, the form :func:`tree_hash` hashes.

    One line, no whitespace between elements, attributes sorted by name. Each
    node is an element named after its type; a subtree node keeps its tag
    (``SubTree``, ``SubTreePlus``) and ``ID``, and holds the inlined tree. Port
    values are the ones after subtree remapping. A type that is not an XML
    name (a py_trees composite such as ``Sequence(memory=True)``) is written
    as ``<_ _type="…">``.

    Example:
        >>> canonical_xml(flat)  # doctest: +SKIP
        '<root beehave_tree_hash="1" format="btcpp-v3"><BehaviorTree ID="Main"><Sequence>…'
    """
    header = {"beehave_tree_hash": str(TREE_HASH_VERSION), "format": flat.format}
    body = _element(flat.root)
    return (
        f"<root{_attributes(header)}><BehaviorTree ID={_quote(flat.id)}>"
        f"{body}</BehaviorTree></root>"
    )


def _element(node: Node) -> str:
    attributes: dict[str, str] = {**node.ports, **node.scripts}
    if node.name is not None:
        attributes["name"] = node.name
    if node.kind is NodeKind.SUBTREE:
        attributes["ID"] = node.ref or ""
    tag = node.type
    if not _XML_NAME.fullmatch(tag):
        attributes["_type"] = tag
        tag = "_"
    children = "".join(_element(child) for child in node.children)
    if not children:
        return f"<{tag}{_attributes(attributes)}/>"
    return f"<{tag}{_attributes(attributes)}>{children}</{tag}>"


def _attributes(attributes: dict[str, str]) -> str:
    # Every name comes from an XML attribute or from Beehave's own adapters.
    return "".join(f" {name}={_quote(value)}" for name, value in sorted(attributes.items()))


def _quote(value: str) -> str:
    # Always double quotes. Tabs and newlines are escaped, because XML would
    # read them back as spaces, so they stay distinct from spaces.
    return '"' + escape(value, _ATTRIBUTE_ENTITIES) + '"'


def _sha256(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = [
    "GRAPH_HASH_VERSION",
    "TREE_HASH_VERSION",
    "canonical_xml",
    "graph_hash",
    "tree_hash",
]
