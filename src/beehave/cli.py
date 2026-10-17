"""The ``beehave`` command line.

Examples::

    beehave graph mission.xml                 # transitions as text
    beehave graph mission.xml -f mermaid -o mission.mmd
    beehave stats mission.xml                 # size, reduction, breakage
    beehave trees mission.xml                 # list the trees in the files
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from beehave import __version__
from beehave.api import analyze
from beehave.config import Config, find_config, load_config
from beehave.errors import BeehaveError
from beehave.parsers import parse_file
from beehave.render import FORMATS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beehave.diagnostics import Diagnostic


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit code.

    Exit codes: 0 on success, 1 when the input cannot be analysed, 2 on a usage error.
    """
    args = _parser().parse_args(argv)
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
    stats.add_argument("--json", action="store_true", help="print the metrics as JSON")
    stats.set_defaults(run=_stats)

    trees = commands.add_parser("trees", help="list the trees defined in the files")
    trees.add_argument("files", nargs="+", type=Path, metavar="FILE", help="BT.CPP XML files")
    trees.add_argument("-c", "--config", type=Path, help="project config (default: ./beehave.yaml)")
    trees.set_defaults(run=_trees)
    return parser


def _common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("files", nargs="+", type=Path, metavar="FILE", help="BT.CPP XML files")
    parser.add_argument("-t", "--tree", help="tree to analyse (default: the main tree)")
    parser.add_argument(
        "-c", "--config", type=Path, help="project config (default: ./beehave.yaml)"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="do not print warnings")


def _config(args: argparse.Namespace) -> Config:
    path = args.config or find_config()
    return load_config(path) if path else Config()


def _graph(args: argparse.Namespace) -> int:
    result = analyze(*args.files, tree=args.tree, config=_config(args))
    _warn(result.graph.diagnostics, quiet=args.quiet)
    output = FORMATS[args.format](result.graph)
    if args.output:
        args.output.write_text(output, encoding="utf-8")
    else:
        sys.stdout.write(output)
    return 0


def _stats(args: argparse.Namespace) -> int:
    result = analyze(*args.files, tree=args.tree, config=_config(args))
    _warn(result.graph.diagnostics, quiet=args.quiet)
    if args.json:
        sys.stdout.write(json.dumps(result.stats.to_dict(), indent=2) + "\n")
    else:
        sys.stdout.write(result.stats.to_text())
    return 0


def _trees(args: argparse.Namespace) -> int:
    document = parse_file(*args.files, config=_config(args))
    for tree_id in document.trees:
        suffix = " (main)" if tree_id == document.main_tree else ""
        sys.stdout.write(f"{tree_id}{suffix}\n")
    return 0


def _warn(diagnostics: Sequence[Diagnostic], *, quiet: bool) -> None:
    if quiet:
        return
    for diagnostic in diagnostics:
        print(f"beehave: {diagnostic}", file=sys.stderr)
