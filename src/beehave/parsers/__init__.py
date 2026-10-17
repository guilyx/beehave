"""Parsers turn a tree file into the shared :mod:`beehave.model`.

Only BehaviorTree.CPP v3 is supported today. The format is detected from the
root element, so a v4 file is refused with a clear message instead of being
misread.
"""

from __future__ import annotations

from beehave.parsers.btcpp_v3 import parse_file, parse_string
from beehave.parsers.detect import detect_string_version, detect_version

__all__ = ["detect_string_version", "detect_version", "parse_file", "parse_string"]
