"""Parsers turn a tree file into the shared :mod:`beehave.model`.

:func:`parse_file` and :func:`parse_string` read BehaviorTree.CPP v3 and v4:
they detect the version (see :mod:`beehave.parsers.detect`) and hand the files
to :mod:`~beehave.parsers.btcpp_v3` or :mod:`~beehave.parsers.btcpp_v4`. Live
py_trees trees are read by :mod:`beehave.parsers.pytrees`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from beehave.parsers import btcpp_v3, btcpp_v4
from beehave.parsers.detect import detect_string_version, detect_version

if TYPE_CHECKING:
    from pathlib import Path

    from beehave.config import Config
    from beehave.model import Document

__all__ = ["detect_string_version", "detect_version", "parse_file", "parse_string"]


def parse_file(*paths: str | Path, config: Config | None = None) -> Document:
    """Parse BT.CPP files, v3 or v4, into a single document.

    Args:
        *paths: The files to read. They must all be in the same BT.CPP version.
        config: Project settings for classifying custom nodes.

    Returns:
        The parsed document; its ``format`` says which version was read.

    Raises:
        ParseError: If a file cannot be read, is not valid, or the files mix versions.
    """
    if detect_version(*paths, config=config) == "4":
        return btcpp_v4.parse_file(*paths, config=config)
    return btcpp_v3.parse_file(*paths, config=config)


def parse_string(
    xml: str | bytes,
    *,
    config: Config | None = None,
    source: str | None = None,
    base_dir: str | Path | None = None,
) -> Document:
    """Parse BT.CPP XML, v3 or v4, held in memory.

    Args:
        xml: The XML text.
        config: Project settings for classifying custom nodes.
        source: A file name for error messages and node locations.
        base_dir: Where relative ``<include>`` paths start from.

    Returns:
        The parsed document; its ``format`` says which version was read.

    Raises:
        ParseError: If the XML is malformed or not a valid BT.CPP document.
    """
    parse = btcpp_v4.parse_string
    if detect_string_version(xml, config=config) != "4":
        parse = btcpp_v3.parse_string
    return parse(xml, config=config, source=source, base_dir=base_dir)
