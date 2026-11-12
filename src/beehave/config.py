"""Per-project configuration.

Beehave works on any tree without configuration. A project only needs a config
file to say which of its custom nodes are conditions "in disguise" (for example
an action that only checks something), to force a node to be an action, or to
say what a custom control or decorator behaves like::

    # beehave.yaml
    conditions:
      - BatteryOK
      - IsEmergency
    actions:
      - Probe
    nodes:                 # custom controls and decorators, by preset
      PipelineSequence: pipeline_sequence
      KeepTrying:
        behaves_like: until_success
    bookkeeping:           # actions that do not act on the world
      - LogMessage
    packages:              # where <include ros_pkg="..."> finds a package
      my_robot_bt: src/my_robot_bt
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from beehave.errors import ConfigError
from beehave.presets import PRESETS, NodePreset, resolve

if TYPE_CHECKING:
    from collections.abc import Mapping

DEFAULT_CONFIG_NAMES = ("beehave.yaml", ".beehave.yaml")
_KNOWN_KEYS = frozenset({"conditions", "actions", "nodes", "bookkeeping", "packages"})


@dataclass(frozen=True)
class Bookkeeping:
    """How a bookkeeping action behaves.

    Attributes:
        never_fails: Whether the action always succeeds. When it may fail,
            its result is a guard on the edges that go through it.
    """

    never_fails: bool = False


@dataclass(frozen=True)
class Config:
    """Project settings that change how nodes are classified.

    Attributes:
        conditions: Node types to treat as conditions, whatever the XML says.
        actions: Node types to treat as actions, whatever the XML says.
        packages: ROS package directories, by package name, for
            ``<include ros_pkg="...">``. They win over a sourced workspace.
        nodes: Custom controls and decorators that behave like a preset, by
            node type (see :mod:`beehave.presets`).
        bookkeeping: Actions that do not act on the world (logging, blackboard
            helpers), by node type. They are left out of the action graph and
            the edges through them are joined up.
    """

    conditions: frozenset[str] = frozenset()
    actions: frozenset[str] = frozenset()
    packages: Mapping[str, Path] = field(default_factory=dict, hash=False)
    nodes: Mapping[str, NodePreset] = field(default_factory=dict, hash=False)
    bookkeeping: Mapping[str, Bookkeeping] = field(default_factory=dict, hash=False)

    def __post_init__(self) -> None:
        both = self.conditions & self.actions
        if both:
            names = ", ".join(sorted(both))
            msg = f"listed as both a condition and an action: {names}"
            raise ConfigError(msg)
        twice = (self.conditions | self.actions) & self.nodes.keys()
        if twice:
            names = ", ".join(sorted(twice))
            msg = f"listed both as a leaf and under nodes: {names}"
            raise ConfigError(msg)
        listed = (self.conditions | self.actions | self.nodes.keys()) & self.bookkeeping.keys()
        if listed:
            names = ", ".join(sorted(listed))
            msg = f"listed under bookkeeping and as another kind of node: {names}"
            raise ConfigError(msg)
        for name, entry in self.nodes.items():
            if entry.behaves_like not in PRESETS:
                msg = f"node {name}: unknown preset '{entry.behaves_like}'"
                raise ConfigError(msg)

    @property
    def declared(self) -> frozenset[str]:
        """Every node type the config describes: conditions, actions, nodes, bookkeeping.

        A declared type is the project's own node, so it is never taken as a
        sign of another format or version (a v3 project may have its own
        ``ParallelAll``).
        """
        return self.conditions | self.actions | frozenset(self.nodes) | frozenset(self.bookkeeping)


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
        nodes=_nodes(data.get("nodes"), source),
        bookkeeping=_bookkeeping(data.get("bookkeeping"), source),
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


def _nodes(value: Any, source: str) -> dict[str, NodePreset]:
    if value is None:
        return {}
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        msg = f"{source}: 'nodes' must map node types to a preset"
        raise ConfigError(msg)
    return {name: _node(name, entry, source) for name, entry in value.items()}


def _node(name: str, entry: Any, source: str) -> NodePreset:
    if isinstance(entry, str):
        entry = {"behaves_like": entry}
    if not isinstance(entry, dict) or not isinstance(entry.get("behaves_like"), str):
        msg = f"{source}: node {name}: give a preset name, or a mapping with 'behaves_like'"
        raise ConfigError(msg)
    preset = resolve(entry["behaves_like"])
    if preset is None:
        known = ", ".join(sorted(PRESETS))
        msg = f"{source}: node {name}: unknown preset '{entry['behaves_like']}'; one of: {known}"
        raise ConfigError(msg)
    options: dict[str, str] = {}
    for option, (allowed, default) in preset.options.items():
        value = entry.get(option, default)
        if not isinstance(value, str) or (allowed is not None and value not in allowed):
            expected = " or ".join(allowed) if allowed else "a string"
            msg = f"{source}: node {name}: '{option}' must be {expected}"
            raise ConfigError(msg)
        options[option] = value
    unknown = sorted(set(entry) - {"behaves_like", *preset.options})
    if unknown:
        msg = f"{source}: node {name}: unknown option(s) for {preset.name}: {', '.join(unknown)}"
        raise ConfigError(msg)
    return NodePreset(preset.name, options)


def _bookkeeping(value: Any, source: str) -> dict[str, Bookkeeping]:
    if value is None:
        return {}
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        return {name: Bookkeeping() for name in value}
    usage = (
        f"{source}: 'bookkeeping' must be a list of node names, or map node names "
        "to {never_fails: true|false}"
    )
    if not isinstance(value, dict):
        raise ConfigError(usage)
    entries: dict[str, Bookkeeping] = {}
    for name, entry in value.items():
        options = {} if entry is None else entry
        if (
            not isinstance(name, str)
            or not isinstance(options, dict)
            or set(options) - {"never_fails"}
            or not isinstance(options.get("never_fails", False), bool)
        ):
            raise ConfigError(usage)
        entries[name] = Bookkeeping(never_fails=options.get("never_fails", False))
    return entries
