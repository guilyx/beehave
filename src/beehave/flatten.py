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

BehaviorTree.CPP v4 (see ``docs/research/btcpp-v4-xml.md`` §5):

- ``<SubTree ID="X" inner="{outer}">`` maps ``{inner}`` to ``{outer}``, and
  ``inner="{=}"`` maps it to the parent's key of the same name.
- ``{@key}`` is the root blackboard's ``key``, from any depth.
- ``inner="literal"`` (also ``${outer}``, a literal in v4) is local.
- ``_autoremap="true"`` maps every other key to itself, except private keys
  that start with ``_``.
- A port written ``{=}`` or ``=`` reads the key named like the port.
- Keys in scripts (``code``, ``if``, ``_skipIf``…) are remapped the same way.
  The scripts on a ``<SubTree>`` element itself read the parent's blackboard.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING

from beehave.diagnostics import Diagnostic
from beehave.errors import FlattenError, TreeSelectionError
from beehave.model import Document, Node, NodeKind, Semantics

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

_TRUE = frozenset({"true", "1"})
_V4 = "btcpp-v4"
# Ports that hold BT.CPP v4 scripts rather than values.
_SCRIPT_PORTS = {
    Semantics.SCRIPT: "code",
    Semantics.SCRIPT_CONDITION: "code",
    Semantics.PRECONDITION: "if",
}
# A script token: a quoted string, a number, or a name (a blackboard key).
_TOKEN = re.compile(r"'[^']*'|\d[\w.]*|[A-Za-z_@]\w*")


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

    @property
    def v4(self) -> bool:
        return self.document.format == _V4

    def inline(self, node: Node, scope: _Scope, stack: tuple[str, ...]) -> Node:
        if node.kind is NodeKind.SUBTREE:
            return self._inline_subtree(node, scope, stack)
        ports = {name: self._rewrite(name, value, scope) for name, value in node.ports.items()}
        script_port = _SCRIPT_PORTS.get(node.semantics)
        if self.v4 and script_port in ports:
            ports[script_port] = _rewrite_script(ports[script_port], scope)
        children = tuple(self.inline(child, scope, stack) for child in node.children)
        return replace(node, ports=ports, children=children, scripts=self._scripts(node, scope))

    def _rewrite(self, port: str, value: str, scope: _Scope) -> str:
        if self.v4 and value.strip() in ("{=}", "="):
            return scope.resolve(port)
        key = _key(value)
        if key is None:
            return value
        if self.v4 and key.startswith("@"):
            return _ROOT_SCOPE.resolve(key[1:])
        return scope.resolve(key)

    def _scripts(self, node: Node, scope: _Scope) -> dict[str, str]:
        return {name: _rewrite_script(code, scope) for name, code in node.scripts.items()}

    def _inline_subtree(self, node: Node, scope: _Scope, stack: tuple[str, ...]) -> Node:
        ref = node.ref or ""
        if ref in stack:
            chain = " -> ".join((*stack, ref))
            msg = f"recursive subtree: {chain}"
            raise FlattenError(msg, node.location)
        tree = self.document.trees.get(ref)
        if tree is None:
            msg = f"subtree '{ref}' is not defined in the loaded files"
            skipped = [d for d in self.document.diagnostics if d.code == "unresolved-include"]
            if skipped:
                notes = "; ".join(f"{d.location}: {d.message}" for d in skipped)
                msg += f"; an <include> was not followed, it may be there: {notes}"
            else:
                msg += "; pass the file that defines it too, or its folder"
            raise FlattenError(msg, node.location)
        inner = self._scope_for(node, ref, scope)
        body = self.inline(tree.root, inner, (*stack, ref))
        # Conditions on the <SubTree> element read the caller's blackboard.
        return replace(node, children=(body,), scripts=self._scripts(node, scope))

    def _scope_for(self, node: Node, ref: str, parent: _Scope) -> _Scope:
        name = parent.prefix + ref
        count = self.instances.get(name, 0) + 1
        self.instances[name] = count
        private_prefix = name if count == 1 else f"{name}#{count}"

        if node.semantics is Semantics.SUBTREE_V4:
            explicit, shared = self._v4_remap(node, parent)
        elif node.semantics is Semantics.SUBTREE_PLUS:
            explicit, shared = self._plus_remap(node, ref, parent)
        else:
            explicit, shared = self._classic_remap(node, ref, parent)
        # In v4, auto-remapping leaves private keys (``_key``) local.
        keeps_private = node.semantics is Semantics.SUBTREE_V4

        def resolve(key: str) -> str:
            if key in explicit:
                return explicit[key]
            if shared and not (keeps_private and key.startswith("_")):
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

    def _v4_remap(self, node: Node, parent: _Scope) -> tuple[dict[str, str], bool]:
        explicit: dict[str, str] = {}
        for inner, value in node.ports.items():
            if inner.startswith("_"):
                continue
            key = inner if value.strip() == "{=}" else _key(value)
            if key is None:
                explicit[inner] = value  # a literal, always local in v4
            elif key.startswith("@"):
                explicit[inner] = _ROOT_SCOPE.resolve(key[1:])
            else:
                explicit[inner] = parent.resolve(key)
        return explicit, _flag(node.ports, "_autoremap")

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


def _rewrite_script(code: str, scope: _Scope) -> str:
    """Remap the blackboard keys a BT.CPP v4 script reads and writes."""

    def substitute(match: re.Match[str]) -> str:
        token = match.group(0)
        if token[0] == "'" or token[0].isdigit() or token in ("true", "false"):
            return token
        if token.startswith("@"):
            return token[1:]
        resolved = scope.resolve(token)
        key = _key(resolved)
        if key is not None:
            return key
        # Remapped to a literal: the script reads that value.
        return resolved if _is_number(resolved) else f"'{resolved}'"

    return _TOKEN.sub(substitute, code)


def _is_number(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True


def _flag(ports: Mapping[str, str], name: str) -> bool:
    return ports.get(name, "").strip().lower() in _TRUE
