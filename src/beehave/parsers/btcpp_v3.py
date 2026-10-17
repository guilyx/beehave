"""Parser for BehaviorTree.CPP v3 XML.

The shared loader in :mod:`beehave.parsers._btcpp` does the work; this module
says what v3 registers out of the box and how it references subtrees. A file
in BT.CPP v4 (by its ``BTCPP_format`` marker or by v4-only nodes, attributes
or port values) is refused with a clear message.

How a user-defined node is classified, strongest signal first:

1. the project config (``conditions:`` / ``actions:``),
2. the explicit XML form (``<Condition ID="X"/>``),
3. the ``<TreeNodesModel>`` declaration,
4. its shape: a leaf is an action, one child a decorator, more a control.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beehave.model import Semantics
from beehave.parsers._btcpp import (
    Builtin,
    Dialect,
    control,
    decorator,
    leaf,
    load_files,
    load_string,
    source_name,
    subtree,
)

if TYPE_CHECKING:
    from pathlib import Path

    from beehave.config import Config
    from beehave.model import Document

__all__ = ["BUILTINS", "DIALECT", "FORMAT", "parse_file", "parse_string", "source_name"]

FORMAT = "btcpp-v3"

BUILTINS: dict[str, Builtin] = {
    "Sequence": control(Semantics.SEQUENCE),
    "SequenceStar": control(Semantics.SEQUENCE_WITH_MEMORY),
    "ReactiveSequence": control(Semantics.REACTIVE_SEQUENCE),
    "Fallback": control(Semantics.FALLBACK),
    "ReactiveFallback": control(Semantics.REACTIVE_FALLBACK),
    "Parallel": control(Semantics.PARALLEL),
    "IfThenElse": control(Semantics.IF_THEN_ELSE, 2, 3),
    "WhileDoElse": control(Semantics.WHILE_DO_ELSE, 3, 3),
    "ManualSelector": control(Semantics.MANUAL_SELECTOR),
    **{f"Switch{n}": control(Semantics.SWITCH, n + 1, n + 1) for n in range(2, 7)},
    "Inverter": decorator(Semantics.INVERTER),
    "ForceSuccess": decorator(Semantics.FORCE_SUCCESS),
    "ForceFailure": decorator(Semantics.FORCE_FAILURE),
    "Repeat": decorator(Semantics.REPEAT),
    "RetryUntilSuccessful": decorator(Semantics.RETRY),
    "KeepRunningUntilFailure": decorator(Semantics.KEEP_RUNNING_UNTIL_FAILURE),
    "Timeout": decorator(Semantics.TIMEOUT),
    "Delay": decorator(Semantics.DELAY),
    "BlackboardCheckInt": decorator(Semantics.BLACKBOARD_CHECK),
    "BlackboardCheckDouble": decorator(Semantics.BLACKBOARD_CHECK),
    "BlackboardCheckString": decorator(Semantics.BLACKBOARD_CHECK),
    "BlackboardCheckBool": decorator(Semantics.BLACKBOARD_CHECK),
    "AlwaysSuccess": leaf(Semantics.ALWAYS_SUCCESS),
    "AlwaysFailure": leaf(Semantics.ALWAYS_FAILURE),
    "SetBlackboard": leaf(Semantics.SET_BLACKBOARD),
    "SubTree": subtree(Semantics.SUBTREE),
    "SubTreePlus": subtree(Semantics.SUBTREE_PLUS),
}

DIALECT = Dialect(
    format=FORMAT,
    version="3",
    builtins=BUILTINS,
    subtree_tags=frozenset({"SubTree", "SubTreePlus"}),
    refuse_other_version="Beehave's v3 parser does not read it; let Beehave detect the version",
)


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
    return load_string(DIALECT, xml, config=config, source=source, base_dir=base_dir)


def parse_file(*paths: str | Path, config: Config | None = None) -> Document:
    """Parse one or more BT.CPP v3 files into a single document.

    Trees from every file (and every file they include) are merged. The main
    tree is taken from the first given file that has a ``main_tree_to_execute``
    attribute, or is the only tree if there is just one. Included files are
    loaded before the trees of the file that includes them, and the first
    definition of a tree ID wins, as in BT.CPP.

    Args:
        *paths: The files to read.
        config: Project settings for classifying custom nodes.

    Returns:
        The parsed document.

    Raises:
        ParseError: If a file cannot be read or is not a valid BT.CPP v3 document.
        UnsupportedFormatError: If a file is in another format (e.g. v4).
    """
    return load_files(DIALECT, paths, config)
