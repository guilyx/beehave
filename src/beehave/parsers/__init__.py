"""Parsers turn a tree file into the shared :mod:`beehave.model`.

Only BehaviorTree.CPP v3 is supported today. The format is detected from the
root element, so a v4 file is refused with a clear message instead of being
misread.
"""

from __future__ import annotations

from beehave.parsers.btcpp_v3 import parse_file, parse_string

__all__ = ["parse_file", "parse_string"]
