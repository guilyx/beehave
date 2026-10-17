"""One call to run the whole pipeline: parse, flatten, walk."""

from __future__ import annotations

from dataclasses import dataclass, replace
from functools import cached_property
from typing import TYPE_CHECKING

from beehave.flatten import FlatTree, flatten
from beehave.parsers import parse_file
from beehave.stats import Stats, compute_stats
from beehave.walk import DEFAULT_MAX_PATHS, build_graph

if TYPE_CHECKING:
    from pathlib import Path

    from beehave.config import Config
    from beehave.graph import ActionGraph
    from beehave.model import Document


@dataclass(frozen=True)
class Analysis:
    """Everything Beehave computed for one tree.

    Attributes:
        document: All trees loaded from the input files.
        tree: The selected tree, with subtrees inlined.
        graph: Its action graph. Its diagnostics include the ones found while loading.
    """

    document: Document
    tree: FlatTree
    graph: ActionGraph

    @cached_property
    def stats(self) -> Stats:
        """The pilot metrics for this tree."""
        return compute_stats(self.tree, self.graph)


def analyze(
    *paths: str | Path,
    tree: str | None = None,
    config: Config | None = None,
    max_paths: int = DEFAULT_MAX_PATHS,
) -> Analysis:
    """Load tree files and build the action graph of one tree.

    Args:
        *paths: BT.CPP XML files. Trees from all of them are merged.
        tree: The tree to analyse; defaults to the main tree.
        config: Project settings (which custom nodes are conditions).
        max_paths: Cap on guarded transitions per action outcome.

    Returns:
        The document, the flattened tree and its action graph.

    Raises:
        beehave.BeehaveError: If the input cannot be read or analysed.

    Example:
        >>> import beehave
        >>> result = beehave.analyze("mission.xml")  # doctest: +SKIP
        >>> print(beehave.to_mermaid(result.graph))  # doctest: +SKIP
    """
    document = parse_file(*paths, config=config)
    flat = flatten(document, tree)
    graph = build_graph(flat, max_paths=max_paths)
    graph = replace(graph, diagnostics=document.diagnostics + graph.diagnostics)
    return Analysis(document, flat, graph)
