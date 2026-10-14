"""Exceptions raised by Beehave."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beehave.model import SourceLocation


class BeehaveError(Exception):
    """Base class for every error Beehave raises on bad input."""

    def __init__(self, message: str, location: SourceLocation | None = None) -> None:
        self.message = message
        self.location = location
        super().__init__(f"{location}: {message}" if location else message)


class ParseError(BeehaveError):
    """A tree file could not be read."""


class UnsupportedFormatError(ParseError):
    """A tree file is in a format this version of Beehave cannot read yet."""


class ConfigError(BeehaveError):
    """A Beehave configuration file is invalid."""


class FlattenError(BeehaveError):
    """Subtrees could not be inlined (missing or recursive subtree)."""


class TreeSelectionError(BeehaveError):
    """No tree, or an unknown tree, was selected for analysis."""
