"""A tiny, safe XML reader that keeps line numbers.

The standard library's ElementTree drops line numbers, and good error messages
need them. This reader builds a minimal element tree with expat directly and
refuses DTDs outright, so entity-expansion tricks cannot reach the parser.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.parsers import expat

from beehave.errors import ParseError
from beehave.model import SourceLocation


@dataclass
class Element:
    """An XML element with the line it started on."""

    tag: str
    attrs: dict[str, str]
    line: int
    children: list[Element] = field(default_factory=list)


def read_xml(data: str | bytes, source: str | None) -> Element:
    """Parse ``data`` into an :class:`Element` tree.

    Args:
        data: The XML text.
        source: The file name, for error messages.

    Returns:
        The root element.

    Raises:
        ParseError: If the XML is not well-formed or declares a DOCTYPE.
    """
    parser = expat.ParserCreate()
    stack: list[Element] = []
    roots: list[Element] = []

    def start(tag: str, attrs: dict[str, str]) -> None:
        element = Element(tag, attrs, parser.CurrentLineNumber)
        (stack[-1].children if stack else roots).append(element)
        stack.append(element)

    def end(_tag: str) -> None:
        stack.pop()

    def doctype(*_args: object) -> None:
        location = SourceLocation(source, parser.CurrentLineNumber)
        msg = "DOCTYPE declarations are not allowed in tree files"
        raise ParseError(msg, location)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.StartDoctypeDeclHandler = doctype

    try:
        parser.Parse(data, True)
    except expat.ExpatError as exc:
        location = SourceLocation(source, exc.lineno)
        msg = f"not well-formed XML: {expat.errors.messages[exc.code]}"
        raise ParseError(msg, location) from exc
    return roots[0]
