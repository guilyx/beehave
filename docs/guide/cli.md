# Command line

```text
beehave graph FILE... [-t TREE] [-f FORMAT] [-o OUTPUT] [-c CONFIG] [-q]
beehave stats FILE... [-t TREE] [--json] [-c CONFIG] [-q]
beehave trees FILE... [-c CONFIG]
beehave --version
```

You can pass several files. Trees from all of them, and from every file they
`<include>`, are merged.

## `beehave graph`

Builds the action graph of one tree.

| Option | Meaning |
| --- | --- |
| `-t`, `--tree TREE` | The tree to analyse. Defaults to `main_tree_to_execute`, or the only tree. |
| `-f`, `--format FORMAT` | `text` (default), `mermaid`, `dot` or `json`. |
| `-o`, `--output FILE` | Write to a file instead of stdout. |
| `-c`, `--config FILE` | Project config. Defaults to `./beehave.yaml` or `./.beehave.yaml` if present. |
| `-q`, `--quiet` | Do not print warnings. |

## `beehave stats`

Prints the Phase 1 metrics for one tree: node counts, actions, reduction,
transitions, longest guard and the approximated node types. `--json` prints
the same numbers as JSON.

## `beehave trees`

Lists the trees defined in the files, marking the main one:

```console
$ beehave trees examples/aerial/drone_mission.xml
DroneMission (main)
ReturnToLaunch
```

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success. Warnings may have been printed. |
| 1 | The input could not be analysed (malformed XML, missing subtree, BT.CPP v4 file, bad config…). The reason is printed on stderr. |
| 2 | Wrong command line usage. |

## Use in CI

Because output is deterministic, you can commit graphs next to your trees and
fail CI when they drift:

```console
$ beehave graph trees/mission.xml -f mermaid -o docs/mission.mmd -q
$ git diff --exit-code docs/mission.mmd
```
