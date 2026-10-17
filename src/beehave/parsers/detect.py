"""Tell which BehaviorTree.CPP version a set of files is written in.

A file says so with ``BTCPP_format="3"`` or ``"4"`` on its root element. Many
files have no marker (BT.CPP v3 never reads it and v4 only warns), so a file
without one is checked for constructs that only exist in v4. A file with
neither (a models-only file, or a tree that is valid in both versions) takes
the version of the other files, and BT.CPP v3 if none says otherwise.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from beehave.config import Config
from beehave.errors import ParseError
from beehave.parsers._btcpp import source_name, v4_evidence
from beehave.parsers._xml import read_xml

if TYPE_CHECKING:
    from beehave.parsers._xml import Element

_EXPLICIT = frozenset({"Action", "Condition", "Decorator", "Control"})


def detect_version(*paths: str | Path, config: Config | None = None) -> str:
    """Return ``"3"`` or ``"4"``: the BT.CPP version the files are written in.

    Args:
        *paths: The files that will be parsed together.
        config: Project settings; node types listed there are never taken as
            evidence of v4, like node types declared in ``TreeNodesModel``.

    Returns:
        The version, ``"3"`` when nothing points to v4.

    Raises:
        ParseError: If a file cannot be read, or if the files mix versions.
    """
    config = config or Config()
    found: dict[str, str] = {}
    for path in paths:
        source = source_name(Path(path))
        try:
            data = Path(path).read_bytes()
        except OSError as exc:
            msg = f"cannot read {source}: {exc.strerror}"
            raise ParseError(msg) from exc
        version = _file_version(read_xml(data, source), config)
        if version is not None:
            found.setdefault(version, source)
    if len(found) > 1:
        msg = f"the files mix BT.CPP v3 ({found['3']}) and v4 ({found['4']})"
        raise ParseError(msg)
    return next(iter(found), "3")


def detect_string_version(xml: str | bytes, *, config: Config | None = None) -> str:
    """Return ``"3"`` or ``"4"`` for XML held in memory."""
    return _file_version(read_xml(xml, None), config or Config()) or "3"


def _file_version(root: Element, config: Config) -> str | None:
    marker = root.attrs.get("BTCPP_format", "").strip()
    if marker in ("3", "4"):
        return marker
    declared = set(config.conditions | config.actions)
    for element in root.children:
        if element.tag == "TreeNodesModel":
            declared |= {m.attrs.get("ID", "") for m in element.children if m.tag in _EXPLICIT}
    for element in root.children:
        if element.tag == "BehaviorTree" and _has_v4_evidence(element, declared):
            return "4"
    return None


def _has_v4_evidence(element: Element, declared: set[str]) -> bool:
    if v4_evidence(element, declared) is not None:
        return True
    return any(_has_v4_evidence(child, declared) for child in element.children)
