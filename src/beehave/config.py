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
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from beehave.errors import ConfigError

DEFAULT_CONFIG_NAMES = ("beehave.yaml", ".beehave.yaml")
_KNOWN_KEYS = frozenset({"conditions", "actions"})


@dataclass(frozen=True)
class Config:
    """Project settings that change how nodes are classified.

    Attributes:
        conditions: Node types to treat as conditions, whatever the XML says.
        actions: Node types to treat as actions, whatever the XML says.
    """

    conditions: frozenset[str] = frozenset()
    actions: frozenset[str] = frozenset()

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
    return config_from_dict(data, source=str(path))


def config_from_dict(data: Any, *, source: str = "config") -> Config:
    """Build a :class:`Config` from already-parsed data.

    Args:
        data: The mapping read from YAML (``None`` means an empty file).
        source: A name for error messages.

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
