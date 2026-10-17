"""Every action graph shown in the README and the docs is real Beehave output.

Each ``mermaid`` block that starts with Beehave's front matter must equal what
``beehave graph <example> -f mermaid`` prints today. To refresh one, run that
command on the example named in the block's ``%% Beehave action graph:`` line.
"""

from __future__ import annotations

import re

import pytest

import beehave
from tests.conftest import EXAMPLES, ROOT

PAGES = [
    "README.md",
    "examples/README.md",
    "docs/index.md",
    "docs/guide/examples.md",
    "docs/design/phase-1.md",
]
EXAMPLE_FILES = {
    "DroneMission": EXAMPLES / "aerial" / "drone_mission.xml",
    "NavigateToGoal": EXAMPLES / "mobile" / "navigate_to_goal.xml",
    "PickAndPlace": EXAMPLES / "manipulation" / "pick_and_place.xml",
}
_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
_HEADER = re.compile(r"^%% Beehave action graph: (\w+) ", re.MULTILINE)


@pytest.mark.parametrize("page", PAGES)
def test_graphs_in_docs_match_beehave_output(page: str) -> None:
    text = (ROOT / page).read_text(encoding="utf-8")
    graphs = [block for block in _BLOCK.findall(text) if _HEADER.search(block)]

    assert graphs, f"{page} shows no Beehave graph"
    for block in graphs:
        header = _HEADER.search(block)
        assert header is not None
        example = EXAMPLE_FILES[header.group(1)]
        assert block == beehave.to_mermaid(beehave.analyze(example).graph), header.group(1)
