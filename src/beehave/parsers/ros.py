"""Find a ROS package's directory, the way BT.CPP does for ``<include ros_pkg>``.

BT.CPP prefixes ``path`` with the package's directory: on ROS 2 its share
directory from the ament index (``ament_index_cpp::get_package_share_directory``),
on ROS 1 the directory ``rospack`` finds (``ros::package::getPath``). Beehave
does the same without needing ROS installed, by reading the environment a
sourced workspace sets:

1. a directory the project names itself (``packages:`` in ``beehave.yaml``,
   or ``--package NAME=DIR``), which wins;
2. ``AMENT_PREFIX_PATH`` (ROS 2): ``<prefix>/share/<name>`` for the first
   prefix whose ament index lists the package;
3. ``ROS_PACKAGE_PATH`` (ROS 1): the first folder below these roots whose
   ``package.xml`` is named ``<name>``.

An installed package usually mirrors its source folder (``install(DIRECTORY
behavior_trees DESTINATION share/${PROJECT_NAME})``), so pointing a package at
its source folder works too.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator, Mapping

# rospack and colcon skip folders that contain one of these files.
_IGNORE_MARKERS = ("CATKIN_IGNORE", "COLCON_IGNORE", "AMENT_IGNORE")
_NAME = re.compile(r"<name>\s*([^<\s]+)\s*</name>")


def find_package(
    name: str,
    packages: Mapping[str, Path] | None = None,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    """Return the directory BT.CPP would use for ``ros_pkg="name"``, or ``None``.

    Args:
        name: The package name.
        packages: Directories the project names itself, by package name.
        env: The environment to read; defaults to ``os.environ``.

    Returns:
        The package directory, or ``None`` when nothing points to it.
    """
    if packages and name in packages:
        return Path(packages[name])
    env = os.environ if env is None else env
    for prefix in _split(env.get("AMENT_PREFIX_PATH")):
        marker = prefix / "share" / "ament_index" / "resource_index" / "packages" / name
        if marker.is_file():
            return prefix / "share" / name
    for root in _split(env.get("ROS_PACKAGE_PATH")):
        for package, package_name in _source_packages(root):
            if package_name == name:
                return package
    return None


def _split(value: str | None) -> list[Path]:
    return [Path(part) for part in (value or "").split(os.pathsep) if part]


def _source_packages(root: Path) -> Iterator[tuple[Path, str]]:
    """Yield the packages below ``root``, in a stable order, like ``rospack``."""
    if not root.is_dir() or any((root / marker).exists() for marker in _IGNORE_MARKERS):
        return
    manifest = root / "package.xml"
    if manifest.is_file():
        match = _NAME.search(manifest.read_text(encoding="utf-8", errors="replace"))
        if match:
            yield root, match.group(1)
        return  # a package's own subfolders are not searched
    try:
        children = sorted(p for p in root.iterdir() if p.is_dir() and not p.name.startswith("."))
    except OSError:  # pragma: no cover - an unreadable folder is skipped, as rospack does
        return
    for child in children:
        yield from _source_packages(child)
