"""The loader shared by the BehaviorTree.CPP parsers (v3 and v4).

A loader reads every ``<BehaviorTree>`` in the given files (following
``<include>`` tags), classifies each node, and checks the structure BT.CPP
itself would check (number of children, required IDs). What differs between
BT.CPP versions (built-in nodes, subtree syntax, format checks) lives in a
:class:`Dialect`. Inlining subtrees is :mod:`beehave.flatten`'s job.

How a user-defined node is classified, strongest signal first:

1. the project config (``conditions:`` / ``actions:``),
2. the explicit XML form (``<Condition ID="X"/>``),
3. the ``<TreeNodesModel>`` declaration,
4. its shape: a leaf is an action, one child a decorator, more a control.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePath
from typing import TYPE_CHECKING

from beehave.config import Config
from beehave.diagnostics import Diagnostic
from beehave.errors import ParseError, UnsupportedFormatError
from beehave.model import Document, Node, NodeKind, Semantics, SourceLocation, Tree
from beehave.parsers._xml import Element, read_xml

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable, Mapping


@dataclass(frozen=True)
class Builtin:
    """A node type BT.CPP registers out of the box."""

    kind: NodeKind
    semantics: Semantics
    min_children: int
    max_children: int | None


def control(semantics: Semantics, lo: int = 1, hi: int | None = None) -> Builtin:
    return Builtin(NodeKind.CONTROL, semantics, lo, hi)


def decorator(semantics: Semantics) -> Builtin:
    return Builtin(NodeKind.DECORATOR, semantics, 1, 1)


def leaf(semantics: Semantics) -> Builtin:
    return Builtin(NodeKind.ACTION, semantics, 0, 0)


def subtree(semantics: Semantics) -> Builtin:
    return Builtin(NodeKind.SUBTREE, semantics, 0, 0)


_EXPLICIT_TAGS: dict[str, NodeKind] = {
    "Action": NodeKind.ACTION,
    "Condition": NodeKind.CONDITION,
    "Decorator": NodeKind.DECORATOR,
    "Control": NodeKind.CONTROL,
}

NOT_PORTS = frozenset({"ID", "name"})

# Names and attributes that only exist in BT.CPP v4. Files often lack the
# BTCPP_format marker, so these are how a v4 file is recognised.
V4_ONLY_NODES = frozenset(
    {
        "SequenceWithMemory",
        "Script",
        "ScriptCondition",
        "Precondition",
        "RunOnce",
        "UnsetBlackboard",
        "Sleep",
        "ParallelAll",
        "AsyncSequence",
        "AsyncFallback",
        "LoopInt",
        "LoopBool",
        "LoopDouble",
        "LoopString",
        "WasEntryUpdated",
        "SkipUnlessUpdated",
        "WaitValueUpdate",
        "TryCatch",
    }
)
V4_ONLY_ATTRIBUTES = frozenset(
    {
        "_skipIf",
        "_failureIf",
        "_successIf",
        "_while",
        "_onSuccess",
        "_onFailure",
        "_post",
        "_onHalted",
        "_autoremap",
    }
)


# BT.CPP v4 pre- and post-conditions: attributes of any node, never ports.
SCRIPT_ATTRIBUTES = frozenset(
    {
        "_failureIf",
        "_successIf",
        "_skipIf",
        "_while",
        "_onSuccess",
        "_onFailure",
        "_post",
        "_onHalted",
    }
)

# py_trees 2.5+ writes XML that looks like BT.CPP v3 but means something else.
_PY_TREES_HINTS = {"Sequence": "memory", "Selector": "memory", "Fallback": "memory"}


def source_name(path: PurePath) -> str:
    """Return how a file is named in locations: always with forward slashes.

    Outputs then read the same on every OS, so committed graphs do not change
    when someone regenerates them on Windows.
    """
    return path.as_posix()


@dataclass(frozen=True)
class Dialect:
    """What one BT.CPP version adds to the shared loader.

    Attributes:
        format: The format name recorded in the document, e.g. ``"btcpp-v3"``.
        version: The ``BTCPP_format`` value this dialect reads.
        builtins: The node types the version registers out of the box.
        subtree_tags: The tags that reference another tree.
        refuse_other_version: The error message used when a file is in the
            other BT.CPP version.
        scripts: Attributes that hold pre- and post-condition scripts.
        drop_private_attributes: Whether other ``_…`` attributes are ignored
            (v4) or kept as ports (v3, where ``__autoremap`` is one).
        last_definition_wins: Which definition of a duplicate tree ID is used.
        unknown_names: Node types that only exist in the other version, with
            what to say when one is used without being declared.
        old_names: Built-in names the version only keeps for compatibility.
        local_main_tree: Whether the only tree of the given files is the main
            tree even when they include other trees (v4).
    """

    format: str
    version: str
    builtins: Mapping[str, Builtin]
    subtree_tags: frozenset[str]
    refuse_other_version: str
    scripts: frozenset[str] = frozenset()
    drop_private_attributes: bool = False
    last_definition_wins: bool = False
    unknown_names: Mapping[str, str] = field(default_factory=dict)
    old_names: Mapping[str, str] = field(default_factory=dict)
    local_main_tree: bool = False


def load_string(
    dialect: Dialect,
    xml: str | bytes,
    *,
    config: Config | None,
    source: str | None,
    base_dir: str | Path | None,
) -> Document:
    """Parse XML held in memory with ``dialect``."""
    loader = Loader(dialect, config or Config())
    loader.load_text(xml, source, Path(base_dir) if base_dir else Path.cwd(), top_level=True)
    return loader.build()


def load_files(dialect: Dialect, paths: Iterable[str | Path], config: Config | None) -> Document:
    """Parse files with ``dialect``, merging their trees into one document."""
    loader = Loader(dialect, config or Config())
    for path in paths:
        loader.load_file(Path(path), top_level=True)
    return loader.build()


@dataclass
class Loader:
    """Reads tree files for one dialect and builds a :class:`Document`."""

    dialect: Dialect
    config: Config
    tree_elements: dict[str, tuple[Element, str | None]] = field(default_factory=dict)
    models: dict[str, NodeKind] = field(default_factory=dict)
    main_tree: str | None = None
    main_tree_location: SourceLocation | None = None
    diagnostics: list[Diagnostic] = field(default_factory=list)
    seen_files: set[Path] = field(default_factory=set)
    local_trees: list[str] = field(default_factory=list)

    # ------------------------------------------------------------- loading ---

    def load_file(
        self, path: Path, *, top_level: bool, included_from: SourceLocation | None = None
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
        self.load_text(data, source_name(path), path.parent, top_level=top_level)

    def load_text(
        self, data: str | bytes, source: str | None, base_dir: Path, *, top_level: bool
    ) -> None:
        root = read_xml(data, source)
        here = SourceLocation(source, root.line)
        if root.tag != "root":
            msg = f"expected <root> as the top element, found <{root.tag}>"
            raise ParseError(msg, here)
        self._check_format(root, here)
        self._reject_py_trees(root, source)

        if top_level and self.main_tree is None and "main_tree_to_execute" in root.attrs:
            self.main_tree = root.attrs["main_tree_to_execute"]
            self.main_tree_location = here

        # Like BT.CPP, load includes before this file's own trees, so an
        # included tree wins over a local tree with the same ID.
        for element in root.children:
            if element.tag == "include":
                self._include(element, base_dir, SourceLocation(source, element.line))
        for element in root.children:
            location = SourceLocation(source, element.line)
            if element.tag == "BehaviorTree":
                self._add_tree(element, source, location, top_level=top_level)
            elif element.tag == "TreeNodesModel":
                self._add_models(element)
            elif element.tag != "include":
                self.diagnostics.append(
                    Diagnostic(
                        "unknown-element",
                        f"ignored unknown element <{element.tag}> under <root>",
                        location=location,
                    )
                )

    def _check_format(self, root: Element, location: SourceLocation) -> None:
        version = root.attrs.get("BTCPP_format")
        if version is None or version == self.dialect.version:
            return
        if version in ("3", "4"):
            msg = f'this file is BT.CPP v{version} (BTCPP_format="{version}"); '
            raise UnsupportedFormatError(msg + self.dialect.refuse_other_version, location)
        self.diagnostics.append(
            Diagnostic(
                "unknown-format-marker",
                f'unknown BTCPP_format="{version}"; '
                f"reading the file as BT.CPP v{self.dialect.version}",
                location=location,
            )
        )

    def _reject_py_trees(self, root: Element, source: str | None) -> None:
        declared = (
            {
                model.attrs.get("ID", "")
                for element in root.children
                if element.tag == "TreeNodesModel"
                for model in element.children
            }
            | self.config.conditions
            | self.config.actions
        )

        def evidence(element: Element) -> Element | None:
            attribute = "policy" if element.tag == "Parallel" else _PY_TREES_HINTS.get(element.tag)
            if attribute in element.attrs and element.tag not in declared:
                return element
            return next((e for c in element.children if (e := evidence(c)) is not None), None)

        for tree in root.children:
            found = evidence(tree) if tree.tag == "BehaviorTree" else None
            if found is not None:
                attribute = "policy" if found.tag == "Parallel" else "memory"
                msg = (
                    f"this file looks like py_trees XML ({attribute}= on <{found.tag}>); "
                    "build the tree with py_trees and read it with --py-trees"
                )
                raise UnsupportedFormatError(msg, SourceLocation(source, found.line))

    def _reject_v4(self, element: Element, source: str | None) -> None:
        declared = self.models.keys() | self.config.conditions | self.config.actions
        evidence = v4_evidence(element, declared)
        if evidence is not None:
            msg = f"this file looks like BT.CPP v4 ({evidence}); "
            location = SourceLocation(source, element.line)
            raise UnsupportedFormatError(msg + self.dialect.refuse_other_version, location)
        for child in element.children:
            self._reject_v4(child, source)

    def _add_tree(
        self, element: Element, source: str | None, location: SourceLocation, *, top_level: bool
    ) -> None:
        tree_id = element.attrs.get("ID")
        if not tree_id:
            msg = "<BehaviorTree> is missing the ID attribute"
            raise ParseError(msg, location)
        if top_level:
            self.local_trees.append(tree_id)
        if tree_id in self.tree_elements:
            which = "last" if self.dialect.last_definition_wins else "first"
            self.diagnostics.append(
                Diagnostic(
                    "duplicate-tree",
                    f"tree '{tree_id}' is defined more than once; the {which} definition is used",
                    location=location,
                )
            )
            if not self.dialect.last_definition_wins:
                return
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
        self.load_file(target, top_level=False, included_from=location)

    # ------------------------------------------------------------ building ---

    def build(self) -> Document:
        if not self.tree_elements:
            msg = "no <BehaviorTree> found"
            raise ParseError(msg)
        if self.dialect.version == "3":
            for element, source in self.tree_elements.values():
                self._reject_v4(element, source)
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
        if main is None and self.dialect.local_main_tree and len(set(self.local_trees)) == 1:
            main = self.local_trees[0]
        return Document(self.dialect.format, trees, main, tuple(self.diagnostics))

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
        dialect = self.dialect
        is_subtree = element.tag in dialect.subtree_tags
        scripts = {k: v for k, v in element.attrs.items() if k in dialect.scripts}
        ports = {
            k: v
            for k, v in element.attrs.items()
            if k not in NOT_PORTS
            and k not in dialect.scripts
            and not (
                dialect.drop_private_attributes
                and k.startswith("_")
                and not (is_subtree and k == "_autoremap")
            )
        }

        explicit_kind = _EXPLICIT_TAGS.get(element.tag)
        builtins = dialect.builtins
        if explicit_kind is not None or is_subtree:
            node_type = element.attrs.get("ID", "")
            if not node_type:
                msg = f"<{element.tag}> needs an ID attribute"
                raise ParseError(msg, location)
        else:
            node_type = element.tag

        if is_subtree:
            ref_builtin = builtins[element.tag]
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
                scripts=scripts,
            )

        if (
            explicit_kind is None
            and not children
            and node_type in self.tree_elements
            and node_type not in builtins
            and node_type not in self.models
            and node_type not in self.config.conditions | self.config.actions
        ):
            self.diagnostics.append(
                Diagnostic(
                    "compact-subtree-reference",
                    f'<{node_type}/> is read as <SubTree ID="{node_type}"/>; '
                    f"BT.CPP {'3.8' if dialect.version == '3' else 'v4'} rejects this short form",
                    location=location,
                )
            )
            reference = builtins[next(iter(sorted(dialect.subtree_tags)))]
            return Node(
                NodeKind.SUBTREE,
                "SubTree",
                reference.semantics,
                name,
                ports,
                ref=node_type,
                location=location,
                scripts=scripts,
            )

        declared = node_type in self.models or node_type in (
            self.config.conditions | self.config.actions
        )
        if node_type in dialect.unknown_names and not declared:
            msg = f"<{node_type}> does not exist in BT.CPP v{dialect.version}; "
            raise ParseError(msg + dialect.unknown_names[node_type], location)

        builtin = builtins.get(node_type)
        if builtin is not None:
            _check_children(
                node_type, builtin.min_children, builtin.max_children, children, location
            )
            if node_type in dialect.old_names:
                self.diagnostics.append(
                    Diagnostic("v3-name", dialect.old_names[node_type], location=location)
                )
            return Node(
                builtin.kind,
                node_type,
                builtin.semantics,
                name,
                ports,
                children,
                location=location,
                scripts=scripts,
            )

        kind = self._classify(node_type, explicit_kind, len(children))
        lo, hi = _ARITY[kind]
        _check_children(node_type, lo, hi, children, location)
        return Node(
            kind,
            node_type,
            Semantics.CUSTOM,
            name,
            ports,
            children,
            location=location,
            scripts=scripts,
        )

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


def v4_evidence(element: Element, declared: Collection[str]) -> str | None:
    """Return why ``element`` can only be BT.CPP v4, or ``None``.

    A node type declared in ``TreeNodesModel`` or the config is never taken as
    evidence, so a v3 project can still have its own ``Sleep`` action.
    """
    if element.tag in V4_ONLY_NODES and element.tag not in declared:
        return f"it uses <{element.tag}>"
    for name, value in element.attrs.items():
        if name in V4_ONLY_ATTRIBUTES:
            return f"it uses the {name} attribute"
        if value.strip() == "{=}" or value.strip().startswith("{@"):
            return f"it uses the port value {value.strip()}"
    if element.tag == "Parallel":
        for name in ("success_count", "failure_count"):
            if name in element.attrs:
                return f"it uses {name} on <Parallel>"
    return None


_ARITY: dict[NodeKind, tuple[int, int | None]] = {
    NodeKind.ACTION: (0, 0),
    NodeKind.CONDITION: (0, 0),
    NodeKind.DECORATOR: (1, 1),
    NodeKind.CONTROL: (1, None),
    NodeKind.SUBTREE: (0, 0),
}


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
