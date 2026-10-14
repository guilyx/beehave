"""The landing-tree graph shown in the README and the docs is real output.

If the renderer changes, regenerate the blocks with:

    beehave graph tests/fixtures/trees/landing.xml -f mermaid -q
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import beehave
from tests.conftest import FIXTURES

ROOT = Path(__file__).resolve().parents[2]
PAGES = ["README.md", "docs/index.md", "docs/design/phase-1.md"]
_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


@pytest.mark.parametrize("page", PAGES)
def test_landing_graph_in_docs_matches_beehave_output(page: str) -> None:
    expected = beehave.to_mermaid(beehave.analyze(FIXTURES / "trees" / "landing.xml").graph)
    blocks = [
        b
        for b in _BLOCK.findall((ROOT / page).read_text(encoding="utf-8"))
        if 'a1["EmergencyLand"]' in b
    ]

    assert blocks, f"{page} has no landing graph"
    assert blocks[0] == expected
