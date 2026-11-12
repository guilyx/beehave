"""Node identity: a stable path for every node, and the ids runtimes give them.

Logs, tests, diffs and editors need to point at one node of a tree. Beehave
gives every node of the instantiated tree (the tree with its subtrees inlined)
three identifiers, all computed from the tree alone:

- A **path** (:attr:`NodeRef.path`), Beehave's stable key. It names each node
  from the root down: its ``name`` if it has one, else its type (for a subtree
  node, the ID of the tree it includes). Siblings that would get the same
  segment are numbered ``#2``, ``#3``… in document order. Adding, removing or
  reordering other nodes does not change it, so diffs and plans keep pointing
  at the same node. In py_trees every behaviour has a name, so the path is the
  names from the root down.
- A **runtime id** (:attr:`NodeRef.uid`, :attr:`NodeRef.index`): the node's
  position in a depth-first, pre-order walk of the instantiated tree, where a
  ``SubTree`` node comes right before the nodes of the tree it includes. Every
  node counts: controls, decorators, conditions, actions and subtree nodes.
  :attr:`IdScheme.BTCPP_V4` starts at 1, like ``TreeNode::UID()`` in
  BehaviorTree.CPP v4; :attr:`IdScheme.PREORDER` starts at 0, for runtimes that
  publish their own indices that way.
- The **runtime path** (:attr:`NodeRef.runtime_path`): ``TreeNode::fullPath()``
  in BehaviorTree.CPP v4, e.g. ``mysub/Sequence::5``, for BT.CPP trees.

BT.CPP v3 numbers nodes per process rather than per tree, so a v3 log must be
matched through the tree it embeds; the ids computed here are what v4 would
give the same tree.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from beehave.model import NodeKind

if TYPE_CHECKING:
    from beehave.flatten import FlatTree
    from beehave.model import Node, SourceLocation

TreePath = tuple[int, ...]
"""Where a node sits in the instantiated tree: child indices from the root."""

_BTCPP_FORMATS = frozenset({"btcpp-v3", "btcpp-v4"})


class IdScheme(str, Enum):
    """How runtime ids are numbered. Both walk the tree in the same order."""

    BTCPP_V4 = "btcpp-v4"
    """From 1, like BehaviorTree.CPP v4's ``TreeNode::UID()``."""
    PREORDER = "preorder"
    """From 0: the root of the main tree is 0."""


@dataclass(frozen=True)
class NodeRef:
    """Which node of the instantiated tree something comes from.

    Attributes:
        path: Beehave's stable key for the node (see :mod:`beehave.ids`).
        uid: The node's BehaviorTree.CPP v4 UID: its pre-order position, from 1.
        runtime_path: BehaviorTree.CPP v4's ``fullPath()`` for the node, or
            ``None`` for formats other than BT.CPP.
    """

    path: str
    uid: int
    runtime_path: str | None = None

    @property
    def index(self) -> int:
        """The node's pre-order position, from 0 (:attr:`IdScheme.PREORDER`)."""
        return self.uid - 1

    def runtime_id(self, scheme: IdScheme = IdScheme.BTCPP_V4) -> int:
        """Return the node's id in ``scheme``."""
        return self.uid if scheme is IdScheme.BTCPP_V4 else self.index


@dataclass(frozen=True)
class RuntimeNode:
    """One node of the instantiated tree, as :func:`runtime_ids` lists it.

    Attributes:
        id: The node's runtime id in the scheme that was asked for.
        ref: All of the node's identifiers.
        parent: The parent's runtime id in the same scheme; ``None`` for the root.
        kind: The role of the node.
        type: The node type, e.g. ``"Sequence"``; ``"SubTree"`` for a subtree node.
        name: The instance name, if the tree gives one.
        subtree: For a subtree node, the ID of the tree it includes.
        location: Where the node was read from, if known.
    """

    id: int
    ref: NodeRef
    parent: int | None
    kind: NodeKind
    type: str
    name: str | None = None
    subtree: str | None = None
    location: SourceLocation | None = None


def node_refs(flat: FlatTree) -> dict[TreePath, NodeRef]:
    """Return the identifiers of every node of a flattened tree, by tree path.

    The tree path is the list of child indices from the root; a subtree node's
    only child is the root of the tree it includes. The result is in pre-order.
    """
    refs: dict[TreePath, NodeRef] = {}
    btcpp = flat.format in _BTCPP_FORMATS

    def visit(node: Node, at: TreePath, path: str, prefix: str) -> None:
        uid = len(refs) + 1
        runtime_path = _runtime_path(node, prefix, uid) if btcpp else None
        refs[at] = NodeRef(path, uid, runtime_path)
        child_prefix = prefix
        if node.kind is NodeKind.SUBTREE and runtime_path is not None:
            # The nodes of an included tree are named after the subtree node.
            child_prefix = runtime_path + "/"
        segments = _segments(node.children)
        for index, child in enumerate(node.children):
            visit(child, (*at, index), f"{path}/{segments[index]}", child_prefix)

    visit(flat.root, (), _segments((flat.root,))[0], "")
    return refs


def runtime_ids(flat: FlatTree, scheme: IdScheme = IdScheme.BTCPP_V4) -> dict[int, RuntimeNode]:
    """Map every runtime id of a flattened tree to its node.

    Every node is listed, not only actions: controls, decorators, conditions
    and subtree nodes have ids too, so a tool holding an id from a log can find
    the node it belongs to, then the vertex or guard that node became.

    Args:
        flat: The instantiated tree, from :func:`beehave.flatten`.
        scheme: How ids are numbered.

    Returns:
        The nodes, by id, in pre-order.

    Example:
        >>> import beehave
        >>> result = beehave.analyze("mission.xml")  # doctest: +SKIP
        >>> beehave.runtime_ids(result.tree)[1].ref.runtime_path  # doctest: +SKIP
        'Sequence::1'
    """
    refs = node_refs(flat)
    nodes: dict[int, RuntimeNode] = {}

    def visit(node: Node, at: TreePath, parent: int | None) -> None:
        ref = refs[at]
        own = ref.runtime_id(scheme)
        is_subtree = node.kind is NodeKind.SUBTREE
        nodes[own] = RuntimeNode(
            own,
            ref,
            parent,
            node.kind,
            node.type,
            node.name,
            node.ref if is_subtree else None,
            node.location,
        )
        for index, child in enumerate(node.children):
            visit(child, (*at, index), own)

    visit(flat.root, (), None)
    return nodes


def _runtime_path(node: Node, prefix: str, uid: int) -> str:
    """``TreeNode::fullPath()`` as BT.CPP v4 builds it (``xml_parsing.cpp``).

    The instance name is the ``name`` attribute, else the registered type (the
    tree ID for a subtree node). When the two are equal, ``::<uid>`` is added.
    """
    type_id = node.ref if node.kind is NodeKind.SUBTREE and node.ref else node.type
    instance = node.name if node.name is not None else type_id
    path = prefix + instance
    return f"{path}::{uid}" if instance == type_id else path


def _segments(siblings: tuple[Node, ...]) -> list[str]:
    """Name each sibling for the path: ``Name``, then ``Name#2``, ``Name#3`` and so on."""
    seen: Counter[str] = Counter()
    segments = []
    for node in siblings:
        base = _escape(_base_name(node))
        seen[base] += 1
        segments.append(base if seen[base] == 1 else f"{base}#{seen[base]}")
    return segments


def _base_name(node: Node) -> str:
    if node.name:
        return node.name
    if node.kind is NodeKind.SUBTREE and node.ref:
        return node.ref
    return node.type


def _escape(segment: str) -> str:
    # "/" separates segments and "#" numbers siblings, so neither may appear raw.
    return segment.replace("%", "%25").replace("/", "%2F").replace("#", "%23")


__all__ = ["IdScheme", "NodeRef", "RuntimeNode", "TreePath", "node_refs", "runtime_ids"]
