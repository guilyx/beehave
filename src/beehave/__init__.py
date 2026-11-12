"""Beehave: the small branch that matters.

Beehave reads a behavior tree and gives back only the actions the robot can
take, in order, with the conditions that lead to each one.

Example:
    >>> import beehave
    >>> result = beehave.analyze("mission.xml")  # doctest: +SKIP
    >>> print(beehave.to_text(result.graph))  # doctest: +SKIP
    START --[not IsBatteryCritical]--> Arm
    ...
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

from beehave.api import Analysis, analyze, analyze_py_trees
from beehave.config import Config, load_config
from beehave.errors import (
    BeehaveError,
    ConfigError,
    FlattenError,
    ParseError,
    TreeSelectionError,
    UnsupportedFormatError,
)
from beehave.flatten import FlatTree, flatten
from beehave.graph import ActionGraph, Condition, Edge, Literal, Outcome, Vertex, VertexKind
from beehave.ids import IdScheme, NodeRef, RuntimeNode, node_refs, runtime_ids
from beehave.parsers import parse_file, parse_string
from beehave.parsers.pytrees import from_py_trees, load_py_trees
from beehave.render import to_dot, to_json, to_mermaid, to_text
from beehave.stats import Stats, compute_stats
from beehave.walk import build_graph

try:
    __version__ = version("beehave-bt")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0+unknown"

__all__ = [
    "ActionGraph",
    "Analysis",
    "BeehaveError",
    "Condition",
    "Config",
    "ConfigError",
    "Edge",
    "FlatTree",
    "FlattenError",
    "IdScheme",
    "Literal",
    "NodeRef",
    "Outcome",
    "ParseError",
    "RuntimeNode",
    "Stats",
    "TreeSelectionError",
    "UnsupportedFormatError",
    "Vertex",
    "VertexKind",
    "__version__",
    "analyze",
    "analyze_py_trees",
    "build_graph",
    "compute_stats",
    "flatten",
    "from_py_trees",
    "load_config",
    "load_py_trees",
    "node_refs",
    "parse_file",
    "parse_string",
    "runtime_ids",
    "to_dot",
    "to_json",
    "to_mermaid",
    "to_text",
]
