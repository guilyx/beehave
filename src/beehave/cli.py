"""The ``beehave`` command line.

Examples::

    beehave graph mission.xml                 # transitions as text
    beehave graph mission.xml -f mermaid -o mission.mmd
    beehave stats mission.xml                 # size, reduction, breakage
    beehave trees mission.xml                 # list the trees in the files
    beehave graph --py-trees robot.trees:create_root   # a py_trees tree (runs that code)
    beehave graph behavior_trees/ -t NavigateToPose     # every tree in a folder
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path
from typing import TYPE_CHECKING

from beehave import __version__
from beehave.api import analyze, analyze_py_trees
from beehave.config import Config, find_config, load_config
from beehave.errors import BeehaveError
from beehave.parsers import parse_file
from beehave.parsers.pytrees import from_py_trees, load_py_trees
from beehave.render import FORMATS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beehave.api import Analysis
    from beehave.diagnostics import Diagnostic
    from beehave.model import Document


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit code.

    Exit codes: 0 on success, 1 when the input cannot be analysed, 2 on a usage error.
    """
    args = _parser().parse_args(argv)
    _check_inputs(args)
    try:
        return int(args.run(args))
    except BeehaveError as exc:
        print(f"beehave: error: {exc}", file=sys.stderr)
        return 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beehave",
        description="Show only the actions a behavior tree can take, and what runs next.",
    )
    parser.add_argument("--version", action="version", version=f"beehave {__version__}")
    commands = parser.add_subparsers(title="commands", required=True, metavar="COMMAND")

    graph = commands.add_parser("graph", help="build the action graph of a tree")
    _common(graph)
    graph.set_defaults(parser=graph)
    graph.add_argument(
        "-f",
        "--format",
        choices=sorted(FORMATS),
        default="text",
        help="output format (default: text)",
    )
    graph.add_argument("-o", "--output", type=Path, help="write to a file instead of stdout")
    graph.set_defaults(run=_graph)

    stats = commands.add_parser("stats", help="print size, reduction and breakage metrics")
    _common(stats)
    stats.set_defaults(parser=stats)
    stats.add_argument("--json", action="store_true", help="print the metrics as JSON")
    stats.set_defaults(run=_stats)

    trees = commands.add_parser("trees", help="list the trees defined in the files")
    _inputs(trees)
    trees.set_defaults(run=_trees, parser=trees)
    return parser


def _inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "files",
        nargs="*",
        type=Path,
        metavar="FILE",
        help="BT.CPP XML files, or folders: every .xml file directly in a folder is read",
    )
    parser.add_argument(
        "--py-trees",
        metavar="SPEC",
        help="read a py_trees tree instead: module:function or file.py:function. "
        "This imports the module and calls the function, so it runs that code",
    )
    parser.add_argument(
        "--kwargs", metavar="JSON", help="arguments for the --py-trees function, as a JSON object"
    )
    parser.add_argument(
        "-c", "--config", type=Path, help="project config (default: ./beehave.yaml)"
    )
    parser.add_argument(
        "--package",
        action="append",
        default=[],
        metavar="NAME=DIR",
        help='where <include ros_pkg="NAME"> finds the package; repeat for several',
    )


def _common(parser: argparse.ArgumentParser) -> None:
    _inputs(parser)
    parser.add_argument("-t", "--tree", help="tree to analyse (default: the main tree)")
    parser.add_argument("-q", "--quiet", action="store_true", help="do not print warnings")


def _check_inputs(args: argparse.Namespace) -> None:
    error = args.parser.error
    for value in args.package:
        name, _, directory = value.partition("=")
        if not name or not directory:
            error("--package takes NAME=DIR, for example --package my_robot_bt=src/my_robot_bt")
    if args.files and args.py_trees:
        error("give tree files or --py-trees, not both")
    if not args.files and not args.py_trees:
        error("give tree files or --py-trees")
    if args.py_trees and getattr(args, "tree", None):
        error("--tree does not apply to --py-trees")
    if args.kwargs is None:
        return
    if not args.py_trees:
        error("--kwargs needs --py-trees")
    try:
        kwargs = json.loads(args.kwargs)
    except json.JSONDecodeError:
        kwargs = None
    if not isinstance(kwargs, dict):
        error("--kwargs must be a JSON object")
    args.kwargs = kwargs


def _config(args: argparse.Namespace) -> Config:
    path = args.config or find_config()
    config = load_config(path) if path else Config()
    if not args.package:
        return config
    packages = dict(config.packages)
    for value in args.package:
        name, _, directory = value.partition("=")
        packages[name] = Path(directory)
    return replace(config, packages=packages)


def _analysis(args: argparse.Namespace) -> Analysis:
    if args.py_trees:
        tree = load_py_trees(args.py_trees, **(args.kwargs or {}))
        return analyze_py_trees(tree, config=_config(args))
    return analyze(*args.files, tree=args.tree, config=_config(args))


def _document(args: argparse.Namespace) -> Document:
    if args.py_trees:
        tree = load_py_trees(args.py_trees, **(args.kwargs or {}))
        return from_py_trees(tree, config=_config(args))
    return parse_file(*args.files, config=_config(args))


def _graph(args: argparse.Namespace) -> int:
    result = _analysis(args)
    _warn(result.graph.diagnostics, quiet=args.quiet)
    output = FORMATS[args.format](result.graph)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


def _stats(args: argparse.Namespace) -> int:
    result = _analysis(args)
    _warn(result.graph.diagnostics, quiet=args.quiet)
    if args.json:
        sys.stdout.write(json.dumps(result.stats.to_dict(), indent=2) + "\n")
    else:
        sys.stdout.write(result.stats.to_text())
    return 0


def _trees(args: argparse.Namespace) -> int:
    document = _document(args)
    for tree_id in document.trees:
        suffix = " (main)" if tree_id == document.main_tree else ""
        sys.stdout.write(f"{tree_id}{suffix}\n")
    return 0


def _warn(diagnostics: Sequence[Diagnostic], *, quiet: bool) -> None:
    if quiet:
        return
    for diagnostic in diagnostics:
        print(f"beehave: {diagnostic}", file=sys.stderr)
