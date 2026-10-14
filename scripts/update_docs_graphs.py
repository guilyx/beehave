"""Refresh the action graphs embedded in the README and the docs.

Every ``mermaid`` block whose ``%% Beehave action graph: <Tree>`` line names one
of the examples is replaced with what Beehave prints for that example today.
``tests/unit/test_docs_examples.py`` fails when a block is stale.

Usage::

    uv run python scripts/update_docs_graphs.py          # rewrite stale blocks
    uv run python scripts/update_docs_graphs.py --check  # exit 1 if any is stale
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import beehave

ROOT = Path(__file__).resolve().parent.parent
PAGES = (
    "README.md",
    "examples/README.md",
    "docs/index.md",
    "docs/guide/examples.md",
    "docs/design/phase-1.md",
)
EXAMPLES = {
    "DroneMission": "examples/aerial/drone_mission.xml",
    "NavigateToGoal": "examples/mobile/navigate_to_goal.xml",
    "PickAndPlace": "examples/manipulation/pick_and_place.xml",
}
_BLOCK = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)
_HEADER = re.compile(r"^%% Beehave action graph: (\w+) ", re.MULTILINE)


def refresh(text: str) -> str:
    """Return ``text`` with every known example graph replaced by current output."""

    def replace(match: re.Match[str]) -> str:
        header = _HEADER.search(match.group(1))
        if header is None or header.group(1) not in EXAMPLES:
            return match.group(0)
        graph = beehave.analyze(ROOT / EXAMPLES[header.group(1)]).graph
        return f"```mermaid\n{beehave.to_mermaid(graph)}```"

    return _BLOCK.sub(replace, text)


def main(argv: list[str] | None = None) -> int:
    """Rewrite stale graph blocks, or only report them with ``--check``."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true", help="only report stale pages")
    args = parser.parse_args(argv)
    stale = []
    for page in PAGES:
        path = ROOT / page
        text = path.read_text(encoding="utf-8")
        new = refresh(text)
        if new != text:
            stale.append(page)
            if not args.check:
                path.write_text(new, encoding="utf-8")
    for page in stale:
        print(f"{'stale' if args.check else 'updated'}: {page}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    sys.exit(main())
