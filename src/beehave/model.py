"""The format-agnostic tree model.

Every parser (BT.CPP v3 today, v4 and py_trees later) turns its input into these
types. The flatten, walk and render steps only ever see this model, so adding a
format means adding a parser and nothing else.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

    from beehave.diagnostics import Diagnostic


class NodeKind(str, Enum):
    """What role a node plays in the tree."""

    CONTROL = "control"
    DECORATOR = "decorator"
    CONDITION = "condition"
    ACTION = "action"
    SUBTREE = "subtree"


class Semantics(str, Enum):
    """The behaviour of a node, independent of the name a library gives it.

    ``SequenceStar`` (BT.CPP v3) and ``SequenceWithMemory`` (BT.CPP v4) are the
    same thing, so both map to :attr:`SEQUENCE_WITH_MEMORY`. User-defined nodes
    are :attr:`CUSTOM`; their :class:`NodeKind` says whether they act or check.
    """

    CUSTOM = "custom"

    # Control nodes.
    SEQUENCE = "sequence"
    SEQUENCE_WITH_MEMORY = "sequence_with_memory"
    REACTIVE_SEQUENCE = "reactive_sequence"
    FALLBACK = "fallback"
    REACTIVE_FALLBACK = "reactive_fallback"
    PARALLEL = "parallel"
    IF_THEN_ELSE = "if_then_else"
    WHILE_DO_ELSE = "while_do_else"
    SWITCH = "switch"
    MANUAL_SELECTOR = "manual_selector"

    # Decorators.
    INVERTER = "inverter"
    FORCE_SUCCESS = "force_success"
    FORCE_FAILURE = "force_failure"
    REPEAT = "repeat"
    RETRY = "retry"
    KEEP_RUNNING_UNTIL_FAILURE = "keep_running_until_failure"
    TIMEOUT = "timeout"
    DELAY = "delay"
    BLACKBOARD_CHECK = "blackboard_check"

    # Built-in leaves.
    ALWAYS_SUCCESS = "always_success"
    ALWAYS_FAILURE = "always_failure"
    SET_BLACKBOARD = "set_blackboard"

    # Subtree references.
    SUBTREE = "subtree"
    SUBTREE_PLUS = "subtree_plus"


@dataclass(frozen=True)
class SourceLocation:
    """Where a node was read from."""

    file: str | None
    line: int | None

    def __str__(self) -> str:
        file = self.file or "<string>"
        return f"{file}:{self.line}" if self.line is not None else file


@dataclass(frozen=True)
class Node:
    """One node of a behavior tree.

    Attributes:
        kind: The role of the node (control, decorator, condition, action, subtree).
        type: The name the source format uses, e.g. ``"SequenceStar"`` or ``"FlyToWaypoint"``.
        semantics: The format-independent behaviour of the node.
        name: The optional instance name (the ``name`` attribute in BT.CPP).
        ports: Port values, exactly as written. ``{key}`` is a blackboard reference.
        children: Child nodes, in order.
        ref: For subtree nodes, the ID of the tree they point to.
        location: Where the node was read from, if known.
    """

    kind: NodeKind
    type: str
    semantics: Semantics = Semantics.CUSTOM
    name: str | None = None
    ports: Mapping[str, str] = field(default_factory=dict)
    children: tuple[Node, ...] = ()
    ref: str | None = None
    location: SourceLocation | None = field(default=None, compare=False)

    @property
    def label(self) -> str:
        """The name to show for this node: its instance name, else its type."""
        return self.name or self.type

    def walk(self) -> Iterator[Node]:
        """Yield this node and all its descendants, depth-first, in document order."""
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass(frozen=True)
class Tree:
    """A named tree (a ``<BehaviorTree>`` in BT.CPP)."""

    id: str
    root: Node
    location: SourceLocation | None = field(default=None, compare=False)


@dataclass(frozen=True)
class Document:
    """Everything loaded from one or more files.

    Attributes:
        format: The source format, e.g. ``"btcpp-v3"``.
        trees: Every tree, by ID.
        main_tree: The tree to analyse by default, if the files say which one.
        diagnostics: Non-fatal problems found while loading.
    """

    format: str
    trees: Mapping[str, Tree]
    main_tree: str | None = None
    diagnostics: tuple[Diagnostic, ...] = ()
