"""Per-project configuration.

Beehave works on any tree without configuration. A project only needs a config
file to say which of its custom nodes are conditions "in disguise" (for example
an action that only checks something), or to force a node to be an action::

    # beehave.yaml
    conditions:
      - BatteryOK
      - IsEmergency
    actions:
      - Probe
    packages:              # where <include ros_pkg="..."> finds a package
      my_robot_bt: src/my_robot_bt
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from beehave.errors import ConfigError

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_CONFIG_NAMES = ("beehave.yaml", ".beehave.yaml")
_KNOWN_KEYS = frozenset({"conditions", "actions", "packages"})


@dataclass(frozen=True)
class Config:
    """Project settings that change how nodes are classified.

    Attributes:
        conditions: Node types to treat as conditions, whatever the XML says.
        actions: Node types to treat as actions, whatever the XML says.
        packages: ROS package directories, by package name, for
            ``<include ros_pkg="...">``. They win over a sourced workspace.
    """

    conditions: frozenset[str] = frozenset()
    actions: frozenset[str] = frozenset()
    packages: Mapping[str, Path] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        both = self.conditions & self.actions
        if both:
            names = ", ".join(sorted(both))
            msg = f"listed as both a condition and an action: {names}"
            raise ConfigError(msg)


def load_config(path: str | Path) -> Config:
    """Read a YAML config file.

    Args:
        path: The file to read.

    Returns:
        The parsed configuration.

    Raises:
        ConfigError: If the file cannot be read or is not a valid config.
    """
    path = Path(path)
    try:
        data: Any = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as exc:
        msg = f"cannot read config file {path}: {exc.strerror}"
        raise ConfigError(msg) from exc
    except yaml.YAMLError as exc:
        msg = f"{path} is not valid YAML: {exc}"
        raise ConfigError(msg) from exc
    return config_from_dict(data, source=str(path), base_dir=path.parent)


def config_from_dict(
    data: Any, *, source: str = "config", base_dir: str | Path | None = None
) -> Config:
    """Build a :class:`Config` from already-parsed data.

    Args:
        data: The mapping read from YAML (``None`` means an empty file).
        source: A name for error messages.
        base_dir: What relative package directories are relative to: the
            config file's folder. Defaults to the current directory.

    Returns:
        The configuration.

    Raises:
        ConfigError: If the data has the wrong shape.
    """
    if data is None:
        return Config()
    if not isinstance(data, dict):
        msg = f"{source}: expected a mapping at the top level"
        raise ConfigError(msg)
    unknown = sorted(set(data) - _KNOWN_KEYS)
    if unknown:
        msg = f"{source}: unknown key(s): {', '.join(map(str, unknown))}"
        raise ConfigError(msg)
    return Config(
        conditions=_names(data.get("conditions"), "conditions", source),
        actions=_names(data.get("actions"), "actions", source),
        packages=_packages(data.get("packages"), source, Path(base_dir or ".")),
    )


def find_config(directory: str | Path = ".") -> Path | None:
    """Return the default config file in ``directory``, if there is one."""
    for name in DEFAULT_CONFIG_NAMES:
        candidate = Path(directory) / name
        if candidate.is_file():
            return candidate
    return None


def _names(value: Any, key: str, source: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        msg = f"{source}: '{key}' must be a list of node names"
        raise ConfigError(msg)
    return frozenset(value)


def _packages(value: Any, source: str, base_dir: Path) -> dict[str, Path]:
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in value.items()
    ):
        msg = f"{source}: 'packages' must map package names to directories"
        raise ConfigError(msg)
    return {name: base_dir / directory for name, directory in value.items()}
