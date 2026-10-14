"""Flatten: inline every subtree so the walk sees one big tree.

Each subtree reference becomes a :attr:`~beehave.model.NodeKind.SUBTREE` node
whose single child is the inlined body. The body's ``{key}`` port values are
rewritten through the reference's remapping, so a node deep inside nested
subtrees shows the blackboard key it really reads.

Remapping rules (BehaviorTree.CPP v3):

- ``<SubTreePlus ID="X" inner="{outer}">`` maps ``{inner}`` to ``{outer}``.
- ``<SubTreePlus ID="X" inner="literal">`` replaces ``{inner}`` with ``literal``.
- ``<SubTreePlus ID="X" __autoremap="true">`` maps every other key to itself.
- ``<SubTree ID="X" inner="outer">`` maps ``{inner}`` to ``{outer}`` (bare names).
- ``<SubTree ID="X" __shared_blackboard="true">`` shares every key.
- Any other key is private to that subtree instance and is shown as
  ``{X/key}`` (``{X#2/key}`` for the second instance of ``X``, and so on).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from beehave.errors import FlattenError, TreeSelectionError
from beehave.model import Document, Node, NodeKind, Semantics

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_TRUE = frozenset({"true", "1"})


@dataclass(frozen=True)
class FlatTree:
    """A tree with every subtree inlined.

    Attributes:
        id: The ID of the tree that was flattened.
        root: The root of the flattened tree.
        format: The source format of the document it came from.
    """

    id: str
    root: Node
    format: str


def select_tree(document: Document, tree_id: str | None = None) -> str:
    """Pick the tree to analyse.

    Args:
        document: The loaded document.
        tree_id: An explicit choice, or ``None`` for the document's main tree.

    Returns:
        The ID of a tree that exists in ``document``.

    Raises:
        TreeSelectionError: If the choice is unknown, or if there is no main
            tree and no choice was made.
    """
    available = ", ".join(sorted(document.trees))
    if tree_id is None:
        if document.main_tree is None:
            msg = f"several trees and no main tree; choose one of: {available}"
            raise TreeSelectionError(msg)
        return document.main_tree
    if tree_id not in document.trees:
        msg = f"tree '{tree_id}' is not defined; choose one of: {available}"
        raise TreeSelectionError(msg)
    return tree_id


def flatten(document: Document, tree_id: str | None = None) -> FlatTree:
    """Inline every subtree reachable from a tree.

    Args:
        document: The loaded document.
        tree_id: The tree to flatten; defaults to the document's main tree.

    Returns:
        The flattened tree.

    Raises:
        TreeSelectionError: If no valid tree is selected.
        FlattenError: If a subtree is missing or includes itself.
    """
    tree_id = select_tree(document, tree_id)
    flattener = _Flattener(document)
    root = flattener.inline(document.trees[tree_id].root, _ROOT_SCOPE, (tree_id,))
    return FlatTree(tree_id, root, document.format)


@dataclass(frozen=True)
class _Scope:
    """How ``{key}`` references resolve inside one subtree instance."""

    prefix: str
    resolve: Callable[[str], str]


_ROOT_SCOPE = _Scope("", lambda key: f"{{{key}}}")


@dataclass
class _Flattener:
    document: Document
    instances: dict[str, int] = field(default_factory=dict)

    def inline(self, node: Node, scope: _Scope, stack: tuple[str, ...]) -> Node:
        if node.kind is NodeKind.SUBTREE:
            return self._inline_subtree(node, scope, stack)
        ports = {name: _rewrite(value, scope) for name, value in node.ports.items()}
        children = tuple(self.inline(child, scope, stack) for child in node.children)
        return replace(node, ports=ports, children=children)

    def _inline_subtree(self, node: Node, scope: _Scope, stack: tuple[str, ...]) -> Node:
        ref = node.ref or ""
        if ref in stack:
            chain = " -> ".join((*stack, ref))
            msg = f"recursive subtree: {chain}"
            raise FlattenError(msg, node.location)
        tree = self.document.trees.get(ref)
        if tree is None:
            msg = f"subtree '{ref}' is not defined in the loaded files"
            raise FlattenError(msg, node.location)
        inner = self._scope_for(node, ref, scope)
        body = self.inline(tree.root, inner, (*stack, ref))
        return replace(node, children=(body,))

    def _scope_for(self, node: Node, ref: str, parent: _Scope) -> _Scope:
        name = parent.prefix + ref
        count = self.instances.get(name, 0) + 1
        self.instances[name] = count
        private_prefix = name if count == 1 else f"{name}#{count}"

        remap = {k: v for k, v in node.ports.items() if not k.startswith("__")}
        if node.semantics is Semantics.SUBTREE_PLUS:
            explicit = {
                inner: parent.resolve(key) if (key := _key(value)) is not None else value
                for inner, value in remap.items()
            }
            shared = _flag(node.ports, "__autoremap")
        else:
            explicit = {inner: parent.resolve(_key(v) or v) for inner, v in remap.items()}
            shared = _flag(node.ports, "__shared_blackboard")

        def resolve(key: str) -> str:
            if key in explicit:
                return explicit[key]
            if shared:
                return parent.resolve(key)
            return f"{{{private_prefix}/{key}}}"

        return _Scope(private_prefix + "/", resolve)


def _key(value: str) -> str | None:
    """Return the blackboard key if ``value`` is a ``{key}`` reference."""
    value = value.strip()
    if len(value) > 2 and value[0] == "{" and value[-1] == "}":
        return value[1:-1]
    return None


def _rewrite(value: str, scope: _Scope) -> str:
    key = _key(value)
    return value if key is None else scope.resolve(key)


def _flag(ports: Mapping[str, str], name: str) -> bool:
    return ports.get(name, "").strip().lower() in _TRUE
