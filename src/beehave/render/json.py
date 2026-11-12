"""JSON rendering: a stable, versioned document for other tools."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from beehave.hashing import graph_hash

if TYPE_CHECKING:
    from beehave.diagnostics import Diagnostic
    from beehave.graph import ActionGraph, Edge, Vertex
    from beehave.ids import NodeRef
    from beehave.model import SourceLocation

SCHEMA = "beehave.action-graph"
VERSION = 1


def to_json(graph: ActionGraph) -> str:
    """Render the graph as a JSON document (schema ``beehave.action-graph``, version 1)."""
    return json.dumps(to_dict(graph), indent=2, ensure_ascii=False) + "\n"


def to_dict(graph: ActionGraph) -> dict[str, Any]:
    """Return the JSON document as Python data."""
    return {
        "schema": SCHEMA,
        "version": VERSION,
        "tree": graph.tree,
        "source_format": graph.format,
        "graph_hash": graph_hash(graph),
        "tree_hash": graph.tree_hash,
        "nodes": [_vertex(v) for v in graph.vertices],
        "edges": [_edge(e) for e in graph.edges],
        "diagnostics": [_diagnostic(d) for d in graph.diagnostics],
    }


def _vertex(vertex: Vertex) -> dict[str, Any]:
    data: dict[str, Any] = {"id": vertex.id, "kind": vertex.kind.value, "label": vertex.label}
    if vertex.type is not None:
        data |= {
            "type": vertex.type,
            "ports": dict(vertex.ports),
            "notes": list(vertex.notes),
            "subtrees": list(vertex.subtrees),
            "location": _location(vertex.location),
            "tree_node": node_ref(vertex.node),
        }
    return data


def _edge(edge: Edge) -> dict[str, Any]:
    return {
        "from": edge.source,
        "to": edge.target,
        "outcome": edge.outcome.value if edge.outcome else None,
        "guard": [
            {
                "condition": lit.condition.label,
                "key": lit.condition.key,
                "holds": lit.positive,
                "tree_node": node_ref(lit.condition.node),
            }
            for lit in edge.guard
        ],
    }


def node_ref(ref: NodeRef | None) -> dict[str, Any] | None:
    """Return a node's identifiers as JSON data: path, uid, index and runtime path."""
    if ref is None:
        return None
    return {
        "path": ref.path,
        "uid": ref.uid,
        "index": ref.index,
        "runtime_path": ref.runtime_path,
    }


def _diagnostic(diagnostic: Diagnostic) -> dict[str, Any]:
    return {
        "code": diagnostic.code,
        "severity": diagnostic.severity.value,
        "message": diagnostic.message,
        "node_type": diagnostic.node_type,
        "location": _location(diagnostic.location),
    }


def _location(location: SourceLocation | None) -> dict[str, Any] | None:
    if location is None:
        return None
    return {"file": location.file, "line": location.line}
