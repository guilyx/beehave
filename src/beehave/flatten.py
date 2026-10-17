"""Flatten: inline every subtree so the walk sees one big tree.

Each subtree reference becomes a :attr:`~beehave.model.NodeKind.SUBTREE` node
whose single child is the inlined body. The body's ``{key}`` port values are
rewritten through the reference's remapping, so a node deep inside nested
subtrees shows the blackboard key it really reads.

Remapping rules (BehaviorTree.CPP 3.8, see ``docs/research/btcpp-v3-xml.md``):

- ``<SubTreePlus ID="X" inner="{outer}">`` (or ``${outer}``) maps ``{inner}``
  to ``{outer}``.
- ``<SubTreePlus ID="X" inner="literal">`` replaces ``{inner}`` with ``literal``.
- ``<SubTreePlus ID="X" __autoremap="true">`` maps every other key to itself.
- ``<SubTree ID="X" inner="outer">`` maps ``{inner}`` to ``{outer}``. Values
  are bare key names: ``inner="{outer}"`` points to a key literally named
  ``{outer}``, which is almost always a mistake, so it is reported.
- ``<SubTree ID="X" __shared_blackboard="true">`` shares every key and
  ignores every other attribute.
- Any other key is private to that subtree instance and is shown as
  ``{X/key}`` (``{X#2/key}`` for the second instance of ``X``, and so on).
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from beehave.diagnostics import Diagnostic
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
        diagnostics: Remapping problems found while inlining.
    """

    id: str
    root: Node
    format: str
    diagnostics: tuple[Diagnostic, ...] = ()


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
    return FlatTree(tree_id, root, document.format, tuple(flattener.diagnostics))


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
    diagnostics: list[Diagnostic] = field(default_factory=list)

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

        if node.semantics is Semantics.SUBTREE_PLUS:
            explicit, shared = self._plus_remap(node, ref, parent)
        else:
            explicit, shared = self._classic_remap(node, ref, parent)

        def resolve(key: str) -> str:
            if key in explicit:
                return explicit[key]
            if shared:
                return parent.resolve(key)
            return f"{{{private_prefix}/{key}}}"

        return _Scope(private_prefix + "/", resolve)

    def _plus_remap(self, node: Node, ref: str, parent: _Scope) -> tuple[dict[str, str], bool]:
        explicit: dict[str, str] = {}
        autoremap_seen = False
        for inner, value in node.ports.items():
            if inner.startswith("_"):
                autoremap_seen = autoremap_seen or (
                    inner == "__autoremap" and _flag(node.ports, inner)
                )
                continue
            key = _key(value, dollar=True)
            if key is not None:
                explicit[inner] = parent.resolve(key)
                continue
            explicit[inner] = value
            if autoremap_seen:
                self._warn(
                    node,
                    "autoremap-literal-order",
                    f"in SubTreePlus '{ref}', {inner}=\"{value}\" comes after __autoremap, "
                    f"so BT.CPP 3.8.4+ also writes it to the parent's '{inner}' key; "
                    "put literals before __autoremap",
                )
        return explicit, _flag(node.ports, "__autoremap")

    def _classic_remap(self, node: Node, ref: str, parent: _Scope) -> tuple[dict[str, str], bool]:
        if _flag(node.ports, "__shared_blackboard"):
            return {}, True
        explicit: dict[str, str] = {}
        for inner, value in node.ports.items():
            if inner.startswith("_"):
                continue
            if _key(value) is not None:
                self._warn(
                    node,
                    "braced-subtree-remap",
                    f"in SubTree '{ref}', {inner}=\"{value}\" points to a key literally named "
                    f"{value}; SubTree takes bare key names (use SubTreePlus for {{key}})",
                )
            explicit[inner] = parent.resolve(value)
        return explicit, False

    def _warn(self, node: Node, code: str, message: str) -> None:
        self.diagnostics.append(
            Diagnostic(code, message, node_type=node.type, location=node.location)
        )


def _key(value: str, *, dollar: bool = False) -> str | None:
    """Return the blackboard key if ``value`` is a ``{key}`` (or ``${key}``) reference."""
    value = value.strip()
    if dollar and value.startswith("${"):
        value = value[1:]
    if len(value) > 2 and value[0] == "{" and value[-1] == "}":
        return value[1:-1]
    return None


def _rewrite(value: str, scope: _Scope) -> str:
    key = _key(value)
    return value if key is None else scope.resolve(key)


def _flag(ports: Mapping[str, str], name: str) -> bool:
    return ports.get(name, "").strip().lower() in _TRUE
