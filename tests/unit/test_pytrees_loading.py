"""Loading py_trees trees: the Python API, factory specs and the command line."""

from __future__ import annotations

import json
import sys
import textwrap
from typing import TYPE_CHECKING

import pytest

import beehave
from beehave.cli import main
from beehave.config import Config
from beehave.errors import BeehaveError, ParseError

pytest.importorskip("py_trees")

import py_trees

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

MISSION = """\
    import py_trees
    from py_trees.common import Status

    from helpers import Step


    class IsReady(py_trees.behaviour.Behaviour):
        def update(self):
            return Status.SUCCESS


    def create_root(retries=3):
        return py_trees.composites.Sequence(
            "Mission",
            memory=True,
            children=[
                IsReady("Ready?"),
                py_trees.decorators.Retry("retry", Step("Go"), num_failures=retries),
            ],
        )


    ROOT = create_root()
    NOT_A_TREE = 42


    def broken():
        raise ValueError("no robot here")
"""

HELPERS = """\
    import py_trees
    from py_trees.common import Status


    class Step(py_trees.behaviour.Behaviour):
        def update(self):
            return Status.SUCCESS
"""

READY = Config(conditions=frozenset({"IsReady"}))


@pytest.fixture(autouse=True)
def _clean_blackboard() -> Iterator[None]:
    yield
    py_trees.blackboard.Blackboard.clear()


@pytest.fixture
def mission(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    (tmp_path / "helpers.py").write_text(textwrap.dedent(HELPERS), encoding="utf-8")
    path = tmp_path / "mission.py"
    path.write_text(textwrap.dedent(MISSION), encoding="utf-8")
    # Loading puts the file's directory on sys.path and registers its modules.
    monkeypatch.setattr(sys, "path", list(sys.path))
    yield path
    for name in ("mission", "helpers", "bad"):
        sys.modules.pop(name, None)


def _root(name: str = "Mission") -> py_trees.behaviour.Behaviour:
    return py_trees.composites.Sequence(name, memory=True, children=[py_trees.timers.Timer()])


# -------------------------------------------------------------------- API ---


def test_analyze_py_trees_runs_the_whole_pipeline() -> None:
    result = beehave.analyze_py_trees(_root())

    assert result.document.format == "py_trees"
    assert result.graph.format == "py_trees"
    assert result.graph.tree == "Mission"
    assert beehave.to_text(result.graph) == ("START --> Timer\nTimer --[success]--> SUCCESS\n")
    assert result.stats.actions == 1


def test_analyze_py_trees_merges_adapter_diagnostics() -> None:
    root = py_trees.composites.Sequence(
        "root",
        memory=True,
        children=[py_trees.behaviours.BlackboardToStatus("Result", "result"), _root("work")],
    )

    codes = [d.code for d in beehave.analyze_py_trees(root).graph.diagnostics]

    assert codes == ["approximated"]


def test_load_py_trees_calls_a_module_factory() -> None:
    root = beehave.load_py_trees("py_trees.demos.sequence:create_root")

    assert isinstance(root, py_trees.composites.Sequence)


def test_load_py_trees_accepts_the_py_trees_render_form() -> None:
    root = beehave.load_py_trees("py_trees.demos.sequence.create_root")

    assert isinstance(root, py_trees.composites.Sequence)


def test_load_py_trees_passes_keyword_arguments() -> None:
    root = beehave.load_py_trees("py_trees.demos.dot_graphs:create_tree", level="all")

    assert root.name == "Demo Dot Graphs all"


def test_load_py_trees_from_a_file_with_sibling_imports(mission: Path) -> None:
    root = beehave.load_py_trees(f"{mission}:create_root", retries=2)

    graph = beehave.analyze_py_trees(root, config=READY).graph
    assert beehave.to_text(graph) == (
        "START --[Ready?]--> Go\n"
        "START --[not Ready?]--> FAILURE\n"
        "Go --[success]--> SUCCESS\n"
        "Go --[failure]--> FAILURE\n"
        "\n"
        "notes:\n"
        "  Go: retry ×2\n"
    )


def test_load_py_trees_returns_a_tree_object_as_is(mission: Path) -> None:
    root = beehave.load_py_trees(f"{mission}:ROOT")

    assert root.name == "Mission"


@pytest.mark.parametrize(
    ("attr", "kwargs", "error", "message"),
    [
        ("broken", {}, ParseError, "calling .*mission.py:broken raised ValueError: no robot here"),
        ("missing", {}, ParseError, "mission.py has no attribute 'missing'"),
        ("NOT_A_TREE", {}, BeehaveError, "neither a py_trees tree nor a function"),
        ("ROOT", {"retries": 1}, BeehaveError, "is a tree, not a function"),
    ],
)
def test_load_py_trees_errors_from_a_file(
    mission: Path, attr: str, kwargs: dict[str, object], error: type[Exception], message: str
) -> None:
    with pytest.raises(error, match=message):
        beehave.load_py_trees(f"{mission}:{attr}", **kwargs)


def test_load_py_trees_reports_an_import_that_raises(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_text("raise RuntimeError('needs ROS')\n", encoding="utf-8")

    with pytest.raises(ParseError, match=r"importing .*bad\.py raised RuntimeError: needs ROS"):
        beehave.load_py_trees(f"{path}:create_root")


def test_load_py_trees_reports_a_module_that_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "needs_ros.py").write_text("raise RuntimeError('no rclpy')\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "path", list(sys.path))

    with pytest.raises(ParseError, match="importing needs_ros:create_root raised RuntimeError"):
        beehave.load_py_trees("needs_ros:create_root")
    sys.modules.pop("needs_ros", None)


def test_load_py_trees_reports_a_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match=r"cannot read .*nowhere\.py: no such file"):
        beehave.load_py_trees(f"{tmp_path / 'nowhere.py'}:create_root")


@pytest.mark.parametrize(
    ("spec", "message"),
    [
        ("no_such_module_xyz:create_root", "cannot import no_such_module_xyz:create_root"),
        ("py_trees.demos.sequence:nothing", "cannot import py_trees.demos.sequence:nothing"),
        (":create_root", "expected package.module:function"),
        ("", "expected package.module:function"),
    ],
)
def test_load_py_trees_reports_a_bad_spec(spec: str, message: str) -> None:
    with pytest.raises(BeehaveError, match=message):
        beehave.load_py_trees(spec)


# -------------------------------------------------------------------- CLI ---


def test_cli_graph(mission: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", "--py-trees", f"{mission}:create_root", "-q"]) == 0

    assert capsys.readouterr().out.startswith("START --> Ready?\n")


def test_cli_reads_the_config(
    mission: Path, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "beehave.yaml"
    config.write_text("conditions: [IsReady]\n", encoding="utf-8")

    assert main(["graph", "--py-trees", f"{mission}:create_root", "-c", str(config)]) == 0

    assert capsys.readouterr().out.startswith("START --[Ready?]--> Go\n")


def test_cli_passes_kwargs(mission: Path, capsys: pytest.CaptureFixture[str]) -> None:
    spec = f"{mission}:create_root"

    assert main(["graph", "--py-trees", spec, "--kwargs", '{"retries": 5}', "-q"]) == 0

    assert "retry ×5" in capsys.readouterr().out


def test_cli_stats(mission: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["stats", "--py-trees", f"{mission}:create_root", "--json", "-q"]) == 0

    assert json.loads(capsys.readouterr().out)["actions"] == 2


def test_cli_trees(mission: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["trees", "--py-trees", f"{mission}:create_root"]) == 0

    assert capsys.readouterr().out == "Mission (main)\n"


def test_cli_reports_a_failing_factory(mission: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["graph", "--py-trees", f"{mission}:broken"]) == 1

    assert "raised ValueError: no robot here" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["graph"], "give tree files or --py-trees"),
        (["graph", "tree.xml", "--py-trees", "m:f"], "give tree files or --py-trees, not both"),
        (["graph", "--py-trees", "m:f", "-t", "Main"], "--tree does not apply to --py-trees"),
        (["graph", "tree.xml", "--kwargs", "{}"], "--kwargs needs --py-trees"),
        (["graph", "--py-trees", "m:f", "--kwargs", "[1]"], "--kwargs must be a JSON object"),
        (["graph", "--py-trees", "m:f", "--kwargs", "{"], "--kwargs must be a JSON object"),
        (["trees"], "give tree files or --py-trees"),
    ],
)
def test_cli_usage_errors(
    args: list[str], message: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        main(args)

    assert exit_info.value.code == 2
    assert message in capsys.readouterr().err
