"""Finding every tree: ROS package includes, and folders of trees.

BT.CPP resolves ``<include ros_pkg="pkg" path="trees/x.xml"/>`` against the
package's directory: its share directory from the ament index on ROS 2, its
``rospack`` directory on ROS 1. Applications such as Nav2 also register every
``.xml`` file of a folder and then pick a tree by ID.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

import beehave
from beehave.cli import main as cli
from beehave.config import Config, load_config
from beehave.errors import FlattenError, ParseError
from beehave.parsers import detect_version, parse_file
from beehave.parsers.ros import find_package

if TYPE_CHECKING:
    from pathlib import Path

MAIN = """<root BTCPP_format="4" main_tree_to_execute="Main">
  <include ros_pkg="my_robot_bt" path="trees/dock.xml"/>
  <BehaviorTree ID="Main">
    <Sequence><SubTree ID="Dock" _autoremap="true"/><Patrol/></Sequence>
  </BehaviorTree>
</root>
"""
DOCK = """<root BTCPP_format="4">
  <BehaviorTree ID="Dock"><Sequence><PlanToDock/><DockRobot/></Sequence></BehaviorTree>
</root>
"""


@pytest.fixture(autouse=True)
def _no_ros_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Tests decide which ROS environment, if any, is "sourced".
    monkeypatch.delenv("AMENT_PREFIX_PATH", raising=False)
    monkeypatch.delenv("ROS_PACKAGE_PATH", raising=False)


def write(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def ament_prefix(root: Path, package: str) -> Path:
    """An install prefix as colcon lays it out, with ``package`` in its ament index."""
    write(root / "share" / "ament_index" / "resource_index" / "packages" / package, "")
    write(root / "share" / package / "trees" / "dock.xml", DOCK)
    return root


def source_package(root: Path, package: str) -> Path:
    write(root / "package.xml", f"<package format='3'>\n  <name>{package}</name>\n</package>\n")
    write(root / "trees" / "dock.xml", DOCK)
    return root


def actions(*paths: str | Path, config: Config | None = None, tree: str | None = None) -> list[str]:
    graph = beehave.analyze(*paths, config=config, tree=tree).graph
    return [v.label for v in graph.actions]


# ------------------------------------------------------------ ros_pkg ---


def test_ros_pkg_from_the_ament_index(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prefix = ament_prefix(tmp_path / "install", "my_robot_bt")
    other = tmp_path / "other"
    other.mkdir()
    monkeypatch.setenv("AMENT_PREFIX_PATH", os.pathsep.join([str(other), str(prefix)]))
    main = write(tmp_path / "app" / "main.xml", MAIN)

    assert actions(main) == ["PlanToDock", "DockRobot", "Patrol"]


def test_ros_pkg_from_ros_package_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    source_package(tmp_path / "src" / "robots" / "my_robot_bt", "my_robot_bt")
    monkeypatch.setenv("ROS_PACKAGE_PATH", str(tmp_path / "src"))
    main = write(tmp_path / "app" / "main.xml", MAIN)

    assert actions(main) == ["PlanToDock", "DockRobot", "Patrol"]


def test_ros_pkg_from_the_config(tmp_path: Path) -> None:
    source_package(tmp_path / "src" / "bt", "my_robot_bt")
    config = write(tmp_path / "beehave.yaml", "packages:\n  my_robot_bt: src/bt\n")
    main = write(tmp_path / "app" / "main.xml", MAIN)

    # Paths in beehave.yaml are relative to the file itself.
    assert actions(main, config=load_config(config)) == ["PlanToDock", "DockRobot", "Patrol"]


def test_the_config_wins_over_a_sourced_workspace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    prefix = ament_prefix(tmp_path / "install", "my_robot_bt")
    write(
        prefix / "share" / "my_robot_bt" / "trees" / "dock.xml",
        DOCK.replace("PlanToDock", "InstalledPlan"),
    )
    monkeypatch.setenv("AMENT_PREFIX_PATH", str(prefix))
    source = source_package(tmp_path / "src" / "bt", "my_robot_bt")
    main = write(tmp_path / "main.xml", MAIN)

    config = Config(packages={"my_robot_bt": source})

    assert actions(main, config=config)[0] == "PlanToDock"


def test_an_unknown_package_is_reported_and_named_in_the_error(tmp_path: Path) -> None:
    main = write(tmp_path / "main.xml", MAIN)

    document = parse_file(main)
    (diagnostic,) = document.diagnostics
    assert diagnostic.code == "unresolved-include"
    assert 'cannot find the ROS package "my_robot_bt"' in diagnostic.message
    assert "--package my_robot_bt=DIR" in diagnostic.message

    with pytest.raises(FlattenError) as error:
        beehave.analyze(main)
    message = str(error.value)
    assert "subtree 'Dock' is not defined in the loaded files" in message
    assert "an <include> was not followed" in message
    assert "main.xml:2" in message


def test_an_absolute_path_ignores_ros_pkg_like_bt_cpp(tmp_path: Path) -> None:
    dock = write(tmp_path / "elsewhere" / "dock.xml", DOCK)
    main = write(tmp_path / "main.xml", MAIN.replace('path="trees/dock.xml"', f'path="{dock}"'))

    document = parse_file(main)

    assert set(document.trees) == {"Main", "Dock"}
    assert [d.code for d in document.diagnostics] == ["ros-pkg-ignored"]


def test_a_missing_file_in_a_found_package_is_an_error(tmp_path: Path) -> None:
    package = tmp_path / "bt"
    package.mkdir()
    main = write(tmp_path / "main.xml", MAIN)

    with pytest.raises(
        ParseError,
        match=r'included file not found: trees/dock\.xml \(in package "my_robot_bt" at .*bt\)',
    ):
        parse_file(main, config=Config(packages={"my_robot_bt": package}))


def test_ros_pkg_works_in_v3_files(tmp_path: Path) -> None:
    source_package(tmp_path / "bt", "my_robot_bt")
    write(
        tmp_path / "bt" / "trees" / "dock.xml",
        '<root><BehaviorTree ID="Dock"><DockRobot/></BehaviorTree></root>',
    )
    main = write(
        tmp_path / "main.xml",
        '<root main_tree_to_execute="Main"><include ros_pkg="my_robot_bt" path="trees/dock.xml"/>'
        '<BehaviorTree ID="Main"><SubTree ID="Dock"/></BehaviorTree></root>',
    )

    assert actions(main, config=Config(packages={"my_robot_bt": tmp_path / "bt"})) == ["DockRobot"]


def test_an_include_without_a_path_is_reported(tmp_path: Path) -> None:
    main = write(
        tmp_path / "main.xml",
        '<root BTCPP_format="4"><include autoapms="pkg::file"/>'
        '<BehaviorTree ID="Main"><Patrol/></BehaviorTree></root>',
    )

    (diagnostic,) = parse_file(main).diagnostics

    assert diagnostic.code == "unresolved-include"
    assert 'autoapms="pkg::file"' in diagnostic.message


# ------------------------------------------------------ find_package ---


def test_find_package_skips_ignored_folders_and_stops_at_packages(tmp_path: Path) -> None:
    source_package(tmp_path / "ignored" / "my_robot_bt", "my_robot_bt")
    write(tmp_path / "ignored" / "COLCON_IGNORE", "")
    outer = source_package(tmp_path / "outer", "outer_pkg")
    source_package(outer / "nested" / "my_robot_bt", "my_robot_bt")
    real = source_package(tmp_path / "real", "my_robot_bt")

    found = find_package("my_robot_bt", env={"ROS_PACKAGE_PATH": str(tmp_path)})

    assert found == real


def test_find_package_without_any_source(tmp_path: Path) -> None:
    assert find_package("my_robot_bt", env={}) is None


# ------------------------------------------------------------ folders ---


def test_a_folder_loads_every_xml_file_in_it(tmp_path: Path) -> None:
    trees = tmp_path / "behavior_trees"
    write(
        trees / "navigate.xml",
        '<root BTCPP_format="4"><BehaviorTree ID="Navigate">'
        '<Sequence><ComputePath/><SubTree ID="Recover"/></Sequence></BehaviorTree></root>',
    )
    write(
        trees / "recover.xml",
        '<root BTCPP_format="4"><BehaviorTree ID="Recover"><Spin/></BehaviorTree></root>',
    )
    write(trees / "notes.txt", "not a tree")
    write(trees / "nested" / "ignored.xml", "<root><BehaviorTree ID='X'><Y/></BehaviorTree></root>")

    assert detect_version(trees) == "4"
    assert set(parse_file(trees).trees) == {"Navigate", "Recover"}
    assert actions(trees, tree="Navigate") == ["ComputePath", "Spin"]


def test_a_folder_and_a_file_together(tmp_path: Path) -> None:
    dock = write(tmp_path / "subtrees" / "dock.xml", DOCK)
    main = write(
        tmp_path / "main.xml",
        MAIN.replace('<include ros_pkg="my_robot_bt" path="trees/dock.xml"/>', ""),
    )

    assert actions(main, dock.parent) == ["PlanToDock", "DockRobot", "Patrol"]


def test_an_empty_folder_is_an_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(ParseError, match=r"no \.xml files in .*empty"):
        parse_file(empty)


# ---------------------------------------------------------------- CLI ---


def test_cli_package_option(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source_package(tmp_path / "bt", "my_robot_bt")
    main = write(tmp_path / "main.xml", MAIN)

    assert cli(["graph", str(main), "--package", f"my_robot_bt={tmp_path / 'bt'}", "-q"]) == 0

    assert capsys.readouterr().out.startswith("START --> PlanToDock\n")


def test_cli_folder_input(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    write(tmp_path / "trees" / "dock.xml", DOCK)

    assert cli(["trees", str(tmp_path / "trees")]) == 0

    assert capsys.readouterr().out == "Dock (main)\n"


@pytest.mark.parametrize("value", ["my_robot_bt", "=dir", "my_robot_bt="])
def test_cli_package_option_needs_name_and_dir(
    value: str, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli(["graph", "t.xml", "--package", value])

    assert exit_info.value.code == 2
    assert "--package takes NAME=DIR" in capsys.readouterr().err


def test_find_package_ignores_manifests_without_a_name_and_other_prefixes(tmp_path: Path) -> None:
    write(tmp_path / "src" / "broken" / "package.xml", "<package format='3'/>")
    empty_prefix = tmp_path / "install_a"
    empty_prefix.mkdir()
    env = {
        "AMENT_PREFIX_PATH": os.pathsep.join([str(empty_prefix), str(tmp_path / "missing")]),
        "ROS_PACKAGE_PATH": os.pathsep.join([str(tmp_path / "src"), str(tmp_path / "nowhere")]),
    }

    assert find_package("broken", env=env) is None
