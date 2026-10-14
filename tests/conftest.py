"""Shared test helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"
GOLDEN = Path(__file__).parent / "golden"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-golden",
        action="store_true",
        default=False,
        help="Rewrite golden files instead of comparing against them.",
    )


@pytest.fixture
def update_golden(request: pytest.FixtureRequest) -> bool:
    return bool(request.config.getoption("--update-golden"))


def tree_xml(body: str, *, main: str | None = "Main", extra: str = "") -> str:
    """Wrap a single tree body in a BT.CPP v3 document."""
    main_attr = f' main_tree_to_execute="{main}"' if main else ""
    return f'<root{main_attr}><BehaviorTree ID="Main">{body}</BehaviorTree>{extra}</root>'
