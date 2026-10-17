"""Beehave on the trees that ship with py_trees, in ``py_trees.demos``.

Every demo factory must convert and walk without errors. The text graph and
the diagnostics of each tree are pinned as snapshots, so any change in
behaviour shows up as a reviewable diff.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest
from syrupy.extensions.single_file import SingleFileSnapshotExtension, WriteMode

import beehave

pytest.importorskip("py_trees")

import py_trees

if TYPE_CHECKING:
    from collections.abc import Iterator

    from syrupy.assertion import SnapshotAssertion

# (name, factory, keyword arguments)
DEMOS: list[tuple[str, str, dict[str, Any]]] = [
    ("sequence", "py_trees.demos.sequence:create_root", {}),
    ("selector", "py_trees.demos.selector:create_root", {}),
    ("eternal-guard", "py_trees.demos.eternal_guard:create_root", {}),
    ("pick-up-where-you-left-off", "py_trees.demos.pick_up_where_you_left_off:create_root", {}),
    ("either-or", "py_trees.demos.either_or:create_root", {}),
    ("context-switching", "py_trees.demos.context_switching:create_root", {}),
    ("blackboard", "py_trees.demos.blackboard:create_root", {}),
    ("display-modes", "py_trees.demos.display_modes:create_root", {}),
    ("logging", "py_trees.demos.logging:create_tree", {}),
    ("stewardship", "py_trees.demos.stewardship:create_tree", {}),
    ("dot-graphs", "py_trees.demos.dot_graphs:create_tree", {"level": "all"}),
]


class _TextSnapshot(SingleFileSnapshotExtension):
    _write_mode = WriteMode.TEXT
    file_extension = "txt"


@pytest.fixture(autouse=True)
def _clean_blackboard() -> Iterator[None]:
    # Some factories register blackboard clients in a process-wide registry.
    yield
    py_trees.blackboard.Blackboard.clear()


@pytest.mark.parametrize(("name", "spec", "kwargs"), DEMOS, ids=[n for n, _, _ in DEMOS])
def test_demo_graph(
    name: str, spec: str, kwargs: dict[str, Any], snapshot: SnapshotAssertion
) -> None:
    result = beehave.analyze_py_trees(beehave.load_py_trees(spec, **kwargs))

    diagnostics = "".join(f"{d}\n" for d in result.graph.diagnostics)
    report = f"{beehave.to_text(result.graph)}\n{result.stats.to_text()}\n{diagnostics}"
    assert report == snapshot(extension_class=_TextSnapshot)


@pytest.mark.parametrize(("name", "spec", "kwargs"), DEMOS, ids=[n for n, _, _ in DEMOS])
def test_demo_renders_in_every_format(name: str, spec: str, kwargs: dict[str, Any]) -> None:
    graph = beehave.analyze_py_trees(beehave.load_py_trees(spec, **kwargs)).graph

    for render in (beehave.to_mermaid, beehave.to_dot, beehave.to_json):
        assert render(graph)


def test_user_classes_are_told_apart_from_builtins_by_owner_class() -> None:
    # stewardship defines its own SuccessEveryN; logging uses py_trees' one.
    def kinds(spec: str) -> dict[str, str]:
        document = beehave.from_py_trees(beehave.load_py_trees(spec))
        root = next(iter(document.trees.values())).root
        return {n.label: n.kind.value for n in root.walk() if not n.children}

    assert kinds("py_trees.demos.logging:create_tree")["EveryN"] == "condition"
    assert kinds("py_trees.demos.stewardship:create_tree")["EveryN"] == "action"
