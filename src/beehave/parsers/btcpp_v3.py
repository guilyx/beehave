"""Parser for BehaviorTree.CPP v3 XML.

The parser reads every ``<BehaviorTree>`` in the given files (following
``<include>`` tags), classifies each node, and checks the structure BT.CPP
itself would check (number of children, required IDs). It does not inline
subtrees; that is :mod:`beehave.flatten`'s job.

How a user-defined node is classified, strongest signal first:

1. the project config (``conditions:`` / ``actions:``),
2. the explicit XML form (``<Condition ID="X"/>``),
3. the ``<TreeNodesModel>`` declaration,
4. its shape: a leaf is an action, one child a decorator, more a control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from beehave.config import Config
from beehave.diagnostics import Diagnostic
from beehave.errors import ParseError, UnsupportedFormatError
from beehave.model import Document, Node, NodeKind, Semantics, SourceLocation, Tree
from beehave.parsers._xml import Element, read_xml

if TYPE_CHECKING:
    from collections.abc import Iterable

FORMAT = "btcpp-v3"


@dataclass(frozen=True)
class Builtin:
    """A node type BT.CPP v3 registers out of the box."""

    kind: NodeKind
    semantics: Semantics
    min_children: int
    max_children: int | None


def _control(semantics: Semantics, lo: int = 1, hi: int | None = None) -> Builtin:
    return Builtin(NodeKind.CONTROL, semantics, lo, hi)


def _decorator(semantics: Semantics) -> Builtin:
    return Builtin(NodeKind.DECORATOR, semantics, 1, 1)


def _leaf(semantics: Semantics) -> Builtin:
    return Builtin(NodeKind.ACTION, semantics, 0, 0)


def _subtree(semantics: Semantics) -> Builtin:
    return Builtin(NodeKind.SUBTREE, semantics, 0, 0)


BUILTINS: dict[str, Builtin] = {
    "Sequence": _control(Semantics.SEQUENCE),
    "SequenceStar": _control(Semantics.SEQUENCE_WITH_MEMORY),
    "ReactiveSequence": _control(Semantics.REACTIVE_SEQUENCE),
    "Fallback": _control(Semantics.FALLBACK),
    "ReactiveFallback": _control(Semantics.REACTIVE_FALLBACK),
    "Parallel": _control(Semantics.PARALLEL),
    "IfThenElse": _control(Semantics.IF_THEN_ELSE, 2, 3),
    "WhileDoElse": _control(Semantics.WHILE_DO_ELSE, 2, 3),
    "ManualSelector": _control(Semantics.MANUAL_SELECTOR),
    **{f"Switch{n}": _control(Semantics.SWITCH, n + 1, n + 1) for n in range(2, 7)},
    "Inverter": _decorator(Semantics.INVERTER),
    "ForceSuccess": _decorator(Semantics.FORCE_SUCCESS),
    "ForceFailure": _decorator(Semantics.FORCE_FAILURE),
    "Repeat": _decorator(Semantics.REPEAT),
    "RetryUntilSuccessful": _decorator(Semantics.RETRY),
    "KeepRunningUntilFailure": _decorator(Semantics.KEEP_RUNNING_UNTIL_FAILURE),
    "Timeout": _decorator(Semantics.TIMEOUT),
    "Delay": _decorator(Semantics.DELAY),
    "BlackboardCheckInt": _decorator(Semantics.BLACKBOARD_CHECK),
    "BlackboardCheckDouble": _decorator(Semantics.BLACKBOARD_CHECK),
    "BlackboardCheckString": _decorator(Semantics.BLACKBOARD_CHECK),
    "AlwaysSuccess": _leaf(Semantics.ALWAYS_SUCCESS),
    "AlwaysFailure": _leaf(Semantics.ALWAYS_FAILURE),
    "SetBlackboard": _leaf(Semantics.SET_BLACKBOARD),
    "SubTree": _subtree(Semantics.SUBTREE),
    "SubTreePlus": _subtree(Semantics.SUBTREE_PLUS),
}

_EXPLICIT_TAGS: dict[str, NodeKind] = {
    "Action": NodeKind.ACTION,
    "Condition": NodeKind.CONDITION,
    "Decorator": NodeKind.DECORATOR,
    "Control": NodeKind.CONTROL,
}

_NOT_PORTS = frozenset({"ID", "name"})


def parse_string(
    xml: str | bytes,
    *,
    config: Config | None = None,
    source: str | None = None,
    base_dir: str | Path | None = None,
) -> Document:
    """Parse BT.CPP v3 XML from a string.

    Args:
        xml: The XML text.
        config: Project settings for classifying custom nodes.
        source: A file name for error messages and node locations.
        base_dir: Where relative ``<include>`` paths start from. Defaults to the
            current directory.

    Returns:
        The parsed document.

    Raises:
        ParseError: If the XML is malformed or not a valid BT.CPP v3 document.
        UnsupportedFormatError: If the document is in another format (e.g. v4).
    """
    loader = _Loader(config or Config())
    loader.load_text(xml, source, Path(base_dir) if base_dir else Path.cwd(), first=True)
    return loader.build()


def parse_file(*paths: str | Path, config: Config | None = None) -> Document:
    """Parse one or more BT.CPP v3 files into a single document.

    Trees from every file (and every file they include) are merged. The main
    tree is taken from the first file's ``main_tree_to_execute`` attribute, or
    is the only tree if there is just one.

    Args:
        *paths: The files to read.
        config: Project settings for classifying custom nodes.

    Returns:
        The parsed document.

    Raises:
        ParseError: If a file cannot be read or is not a valid BT.CPP v3 document.
        UnsupportedFormatError: If a file is in another format (e.g. v4).
    """
    loader = _Loader(config or Config())
    for index, path in enumerate(paths):
        loader.load_file(Path(path), first=index == 0)
    return loader.build()


@dataclass
class _Loader:
    config: Config
    tree_elements: dict[str, tuple[Element, str | None]] = field(default_factory=dict)
    models: dict[str, NodeKind] = field(default_factory=dict)
    main_tree: str | None = None
    main_tree_location: SourceLocation | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    seen_files: set[Path] = field(default_factory=set)

    # ------------------------------------------------------------- loading ---

    def load_file(
        self, path: Path, *, first: bool, included_from: SourceLocation | None = None
    ) -> None:
        resolved = path.resolve()
        if resolved in self.seen_files:
            return
        self.seen_files.add(resolved)
        try:
            data = path.read_bytes()
        except OSError as exc:
            msg = f"cannot read {path}: {exc.strerror}"
            raise ParseError(msg, included_from) from exc
        self.load_text(data, str(path), path.parent, first=first)

    def load_text(
        self, data: str | bytes, source: str | None, base_dir: Path, *, first: bool
    ) -> None:
        root = read_xml(data, source)
        here = SourceLocation(source, root.line)
        if root.tag != "root":
            msg = f"expected <root> as the top element, found <{root.tag}>"
            raise ParseError(msg, here)
        _check_format(root, here)

        if first and "main_tree_to_execute" in root.attrs:
            self.main_tree = root.attrs["main_tree_to_execute"]
            self.main_tree_location = here

        for element in root.children:
            location = SourceLocation(source, element.line)
            if element.tag == "BehaviorTree":
                self._add_tree(element, source, location)
            elif element.tag == "TreeNodesModel":
                self._add_models(element)
            elif element.tag == "include":
                self._include(element, base_dir, location)
            else:
                self.diagnostics.append(
                    Diagnostic(
                        "unknown-element",
                        f"ignored unknown element <{element.tag}> under <root>",
                        location=location,
                    )
                )

    def _add_tree(self, element: Element, source: str | None, location: SourceLocation) -> None:
        tree_id = element.attrs.get("ID")
        if not tree_id:
            msg = "<BehaviorTree> is missing the ID attribute"
            raise ParseError(msg, location)
        if tree_id in self.tree_elements:
            msg = f"tree '{tree_id}' is defined twice"
            raise ParseError(msg, location)
        self.tree_elements[tree_id] = (element, source)

    def _add_models(self, element: Element) -> None:
        for model in element.children:
            kind = _EXPLICIT_TAGS.get(model.tag)
            node_id = model.attrs.get("ID")
            if kind is not None and node_id:
                self.models[node_id] = kind

    def _include(self, element: Element, base_dir: Path, location: SourceLocation) -> None:
        path = element.attrs.get("path")
        if "ros_pkg" in element.attrs or not path:
            self.diagnostics.append(
                Diagnostic(
                    "unresolved-include",
                    "ROS package includes are not followed; pass the included file explicitly",
                    location=location,
                )
            )
            return
        target = Path(path)
        if not target.is_absolute():
            target = base_dir / target
        if not target.is_file():
            msg = f"included file not found: {path}"
            raise ParseError(msg, location)
        self.load_file(target, first=False, included_from=location)

    # ------------------------------------------------------------ building ---

    def build(self) -> Document:
        if not self.tree_elements:
            msg = "no <BehaviorTree> found"
            raise ParseError(msg)
        trees = {
            tree_id: self._build_tree(tree_id, element, source)
            for tree_id, (element, source) in self.tree_elements.items()
        }
        main = self.main_tree
        if main is not None and main not in trees:
            msg = f"main_tree_to_execute '{main}' is not defined"
            raise ParseError(msg, self.main_tree_location)
        if main is None and len(trees) == 1:
            main = next(iter(trees))
        return Document(FORMAT, trees, main, tuple(self.diagnostics))

    def _build_tree(self, tree_id: str, element: Element, source: str | None) -> Tree:
        location = SourceLocation(source, element.line)
        if len(element.children) != 1:
            msg = f"tree '{tree_id}' must have exactly one child, found {len(element.children)}"
            raise ParseError(msg, location)
        return Tree(tree_id, self._build_node(element.children[0], source), location)

    def _build_node(self, element: Element, source: str | None) -> Node:
        location = SourceLocation(source, element.line)
        children = tuple(self._build_node(child, source) for child in element.children)
        name = element.attrs.get("name")
        ports = {k: v for k, v in element.attrs.items() if k not in _NOT_PORTS}

        explicit_kind = _EXPLICIT_TAGS.get(element.tag)
        if explicit_kind is not None or element.tag in ("SubTree", "SubTreePlus"):
            node_type = element.attrs.get("ID", "")
            if not node_type:
                msg = f"<{element.tag}> needs an ID attribute"
                raise ParseError(msg, location)
        else:
            node_type = element.tag

        if element.tag in ("SubTree", "SubTreePlus"):
            ref_builtin = BUILTINS[element.tag]
            _check_children(
                element.tag, ref_builtin.min_children, ref_builtin.max_children, children, location
            )
            return Node(
                NodeKind.SUBTREE,
                element.tag,
                ref_builtin.semantics,
                name,
                ports,
                children,
                ref=node_type,
                location=location,
            )

        builtin = BUILTINS.get(node_type)
        if builtin is not None:
            _check_children(
                node_type, builtin.min_children, builtin.max_children, children, location
            )
            return Node(
                builtin.kind, node_type, builtin.semantics, name, ports, children, location=location
            )

        kind = self._classify(node_type, explicit_kind, len(children))
        lo, hi = _ARITY[kind]
        _check_children(node_type, lo, hi, children, location)
        return Node(kind, node_type, Semantics.CUSTOM, name, ports, children, location=location)

    def _classify(self, node_type: str, explicit: NodeKind | None, n_children: int) -> NodeKind:
        if node_type in self.config.conditions:
            return NodeKind.CONDITION
        if node_type in self.config.actions:
            return NodeKind.ACTION
        if explicit is not None:
            return explicit
        if node_type in self.models:
            return self.models[node_type]
        if n_children == 0:
            return NodeKind.ACTION
        return NodeKind.DECORATOR if n_children == 1 else NodeKind.CONTROL


_ARITY: dict[NodeKind, tuple[int, int | None]] = {
    NodeKind.ACTION: (0, 0),
    NodeKind.CONDITION: (0, 0),
    NodeKind.DECORATOR: (1, 1),
    NodeKind.CONTROL: (1, None),
    NodeKind.SUBTREE: (0, 0),
}


def _check_format(root: Element, location: SourceLocation) -> None:
    version = root.attrs.get("BTCPP_format")
    if version is None or version == "3":
        return
    if version == "4":
        msg = (
            'this file is BT.CPP v4 (BTCPP_format="4"); '
            "Beehave reads BT.CPP v3 for now, v4 support is on the roadmap"
        )
    else:
        msg = f'unknown BTCPP_format "{version}"'
    raise UnsupportedFormatError(msg, location)


def _check_children(
    node_type: str,
    lo: int,
    hi: int | None,
    children: Iterable[Node],
    location: SourceLocation,
) -> None:
    count = len(tuple(children))
    if lo <= count and (hi is None or count <= hi):
        return
    if hi == 0:
        msg = f"<{node_type}> cannot have children"
    elif hi is None:
        msg = f"<{node_type}> needs at least {lo} child{'ren' if lo > 1 else ''}, found {count}"
    elif lo == hi:
        msg = f"<{node_type}> needs exactly {lo} child{'ren' if lo > 1 else ''}, found {count}"
    else:
        msg = f"<{node_type}> needs {lo} to {hi} children, found {count}"
    raise ParseError(msg, location)
