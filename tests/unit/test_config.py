"""Project configuration file."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beehave.config import Config, config_from_dict, find_config, load_config
from beehave.errors import ConfigError

if TYPE_CHECKING:
    from pathlib import Path


def test_load_lists(tmp_path: Path) -> None:
    path = tmp_path / "beehave.yaml"
    path.write_text("conditions:\n  - BatteryOK\nactions: [Probe]\n")

    assert load_config(path) == Config(
        conditions=frozenset({"BatteryOK"}), actions=frozenset({"Probe"})
    )


def test_empty_file_is_an_empty_config(tmp_path: Path) -> None:
    path = tmp_path / "beehave.yaml"
    path.write_text("")

    assert load_config(path) == Config()


@pytest.mark.parametrize(
    ("data", "message"),
    [
        ([1, 2], "expected a mapping"),
        ({"condition": ["A"]}, "unknown key"),
        ({"conditions": "A"}, "must be a list"),
        ({"conditions": [1]}, "must be a list"),
        ({"conditions": ["A"], "actions": ["A"]}, "both a condition and an action: A"),
    ],
)
def test_invalid_configs(data: object, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        config_from_dict(data)


def test_invalid_yaml(tmp_path: Path) -> None:
    path = tmp_path / "beehave.yaml"
    path.write_text("conditions: [\n")

    with pytest.raises(ConfigError, match="not valid YAML"):
        load_config(path)


def test_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="cannot read"):
        load_config(tmp_path / "nope.yaml")


def test_find_config(tmp_path: Path) -> None:
    assert find_config(tmp_path) is None

    (tmp_path / ".beehave.yaml").write_text("")
    assert find_config(tmp_path) == tmp_path / ".beehave.yaml"

    (tmp_path / "beehave.yaml").write_text("")
    assert find_config(tmp_path) == tmp_path / "beehave.yaml"


def test_packages_are_relative_to_the_config_file(tmp_path: Path) -> None:
    path = tmp_path / "beehave.yaml"
    path.write_text("packages:\n  my_robot_bt: src/bt\n  other: /opt/ros/share/other\n")

    packages = load_config(path).packages

    assert packages == {
        "my_robot_bt": tmp_path / "src" / "bt",
        "other": tmp_path / "/opt/ros/share/other",
    }


@pytest.mark.parametrize("value", [["a"], {"a": 1}, "a"])
def test_packages_must_map_names_to_directories(value: object) -> None:
    with pytest.raises(ConfigError, match="'packages' must map package names to directories"):
        config_from_dict({"packages": value})
