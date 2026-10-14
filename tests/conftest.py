"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "tests" / "fixtures"
EXAMPLES = ROOT / "examples"


def tree_xml(body: str, *, main: str | None = "Main", extra: str = "") -> str:
    """Wrap a single tree body in a BT.CPP v3 document."""
    main_attr = f' main_tree_to_execute="{main}"' if main else ""
    return f'<root{main_attr}><BehaviorTree ID="Main">{body}</BehaviorTree>{extra}</root>'
