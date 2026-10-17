"""Parser for BehaviorTree.CPP v4 XML.

The shared loader in :mod:`beehave.parsers._btcpp` does the work; this module
says what v4 registers out of the box (BT.CPP 4.10, see
``docs/research/btcpp-v4-xml.md``) and how v4 differs from v3 when loading:

- pre- and post-conditions (``_skipIf``, ``_onSuccess``…) are scripts kept
  apart from the ports, and other ``_…`` attributes are ignored;
- ``<SubTree>`` is the only subtree reference, with v4 remapping;
- the last definition of a duplicate tree ID wins;
- without ``main_tree_to_execute``, the only tree of the given files is the
  main tree, even when they include other trees.

How a user-defined node is classified is the same as in v3.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beehave.model import NodeKind, Semantics
from beehave.parsers._btcpp import (
    SCRIPT_ATTRIBUTES,
    Builtin,
    Dialect,
    control,
    decorator,
    leaf,
    load_files,
    load_string,
    subtree,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beehave.config import Config
    from beehave.model import Document

__all__ = ["BUILTINS", "DIALECT", "FORMAT", "parse_file", "parse_string"]

FORMAT = "btcpp-v4"

BUILTINS: dict[str, Builtin] = {
    "Sequence": control(Semantics.SEQUENCE),
    # The async versions yield after each child; the edges are the same.
    "AsyncSequence": control(Semantics.SEQUENCE),
    "SequenceWithMemory": control(Semantics.SEQUENCE_WITH_MEMORY),
    "SequenceStar": control(Semantics.SEQUENCE_WITH_MEMORY),
    "ReactiveSequence": control(Semantics.REACTIVE_SEQUENCE),
    "Fallback": control(Semantics.FALLBACK),
    "AsyncFallback": control(Semantics.FALLBACK),
    "ReactiveFallback": control(Semantics.REACTIVE_FALLBACK),
    "Parallel": control(Semantics.PARALLEL),
    "ParallelAll": control(Semantics.PARALLEL_ALL),
    "IfThenElse": control(Semantics.IF_THEN_ELSE, 2, 3),
    "WhileDoElse": control(Semantics.WHILE_DO_ELSE, 2, 3),
    "TryCatch": control(Semantics.TRY_CATCH, 2),
    **{f"Switch{n}": control(Semantics.SWITCH, n + 1, n + 1) for n in range(2, 7)},
    "Inverter": decorator(Semantics.INVERTER),
    "ForceSuccess": decorator(Semantics.FORCE_SUCCESS),
    "ForceFailure": decorator(Semantics.FORCE_FAILURE),
    "Repeat": decorator(Semantics.REPEAT),
    "RetryUntilSuccessful": decorator(Semantics.RETRY),
    "KeepRunningUntilFailure": decorator(Semantics.KEEP_RUNNING_UNTIL_FAILURE),
    "Timeout": decorator(Semantics.TIMEOUT),
    "Delay": decorator(Semantics.DELAY),
    # Waits until the entry changes, then ticks its child: like a delay.
    "WaitValueUpdate": decorator(Semantics.DELAY),
    "RunOnce": decorator(Semantics.RUN_ONCE),
    "Precondition": decorator(Semantics.PRECONDITION),
    "SkipUnlessUpdated": decorator(Semantics.SKIP_UNLESS_UPDATED),
    **{f"Loop{t}": decorator(Semantics.LOOP_QUEUE) for t in ("Int", "Bool", "Double", "String")},
    "AlwaysSuccess": leaf(Semantics.ALWAYS_SUCCESS),
    "AlwaysFailure": leaf(Semantics.ALWAYS_FAILURE),
    "SetBlackboard": leaf(Semantics.SET_BLACKBOARD),
    "UnsetBlackboard": leaf(Semantics.SET_BLACKBOARD),
    "Script": leaf(Semantics.SCRIPT),
    "Sleep": leaf(Semantics.WAIT),
    "ScriptCondition": Builtin(NodeKind.CONDITION, Semantics.SCRIPT_CONDITION, 0, 0),
    # Registered as an action, but it only checks whether an entry changed.
    "WasEntryUpdated": Builtin(NodeKind.CONDITION, Semantics.ENTRY_UPDATED, 0, 0),
    "SubTree": subtree(Semantics.SUBTREE_V4),
}

_USE_SUBTREE = 'use <SubTree ID="…" _autoremap="true"/> and {key} values'
_REMOVED = "declare it in <TreeNodesModel> if your project registers a node with this name"

DIALECT = Dialect(
    format=FORMAT,
    version="4",
    builtins=BUILTINS,
    subtree_tags=frozenset({"SubTree"}),
    refuse_other_version="Beehave's v4 parser does not read it; let Beehave detect the version",
    scripts=SCRIPT_ATTRIBUTES,
    drop_private_attributes=True,
    last_definition_wins=True,
    unknown_names={
        "SubTreePlus": _USE_SUBTREE,
        **{f"BlackboardCheck{t}": _REMOVED for t in ("Int", "Double", "String", "Bool")},
        "ManualSelector": _REMOVED,
    },
    old_names={
        "SequenceStar": (
            "SequenceStar is the v3 name of SequenceWithMemory; BT.CPP v4 only registers it "
            "when built with USE_BTCPP3_OLD_NAMES"
        ),
    },
    local_main_tree=True,
)


def parse_string(
    xml: str | bytes,
    *,
    config: Config | None = None,
    source: str | None = None,
    base_dir: str | Path | None = None,
) -> Document:
    """Parse BT.CPP v4 XML from a string.

    Args:
        xml: The XML text.
        config: Project settings for classifying custom nodes.
        source: A file name for error messages and node locations.
        base_dir: Where relative ``<include>`` paths start from. Defaults to the
            current directory.

    Returns:
        The parsed document.

    Raises:
        ParseError: If the XML is malformed or not a valid BT.CPP v4 document.
        UnsupportedFormatError: If the document is in another format (e.g. v3).
    """
    return load_string(DIALECT, xml, config=config, source=source, base_dir=base_dir)


def parse_file(*paths: str | Path, config: Config | None = None) -> Document:
    """Parse one or more BT.CPP v4 files into a single document.

    Trees from every file (and every file they include) are merged. Included
    files are loaded before the trees of the file that includes them, and the
    last definition of a tree ID wins, as in BT.CPP v4.

    Args:
        *paths: The files to read.
        config: Project settings for classifying custom nodes.

    Returns:
        The parsed document.

    Raises:
        ParseError: If a file cannot be read or is not a valid BT.CPP v4 document.
        UnsupportedFormatError: If a file is in another format (e.g. v3).
    """
    return load_files(DIALECT, paths, config)
