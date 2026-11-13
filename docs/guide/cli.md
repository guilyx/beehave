# Command line

```text
beehave graph FILE... [-t TREE] [-f FORMAT] [-o OUTPUT] [--print-hash] [-c CONFIG] [--package NAME=DIR] [-q]
beehave graph --py-trees SPEC [--kwargs JSON] [-f FORMAT] [-o OUTPUT] [-c CONFIG] [-q]
beehave stats FILE... [-t TREE] [--json] [-c CONFIG] [-q]
beehave stats --py-trees SPEC [--kwargs JSON] [--json] [-c CONFIG] [-q]
beehave ids FILE... [-t TREE] [--scheme SCHEME] [--json] [-c CONFIG] [-q]
beehave ids --py-trees SPEC [--kwargs JSON] [--scheme SCHEME] [--json] [-c CONFIG] [-q]
beehave diff OLD NEW [-t TREE] [-f FORMAT] [-o OUTPUT] [--exit-code] [-c CONFIG] [--package NAME=DIR] [-q]
beehave trees FILE... [-c CONFIG]
beehave trees --py-trees SPEC [--kwargs JSON] [-c CONFIG]
beehave --version
```

`FILE` is BehaviorTree.CPP XML, v3 or v4: Beehave detects the version (see
[Formats](formats.md)). You can pass several files, and folders: a folder
stands for every `.xml` file directly in it. Trees from all of them, and from
every file they `<include>`, are merged; they must all be in the same BT.CPP
version. See [Subtrees and includes](subtrees.md).

`--py-trees SPEC` reads a py_trees tree instead. **It imports a module and
calls a function, so it runs that code**: only point it at code you would run
yourself.

## `beehave graph`

Builds the action graph of one tree.

| Option | Meaning |
| --- | --- |
| `-t`, `--tree TREE` | The tree to analyse. Defaults to `main_tree_to_execute`, or the only tree. Not used with `--py-trees`. |
| `--py-trees SPEC` | Read a py_trees tree: `package.module:function` or `path/to/file.py:function`. The function is called, and must return a `Behaviour` or a `BehaviourTree`; `SPEC` may also name such an object. |
| `--kwargs JSON` | Arguments for the `--py-trees` function, as a JSON object, e.g. `'{"level": "all"}'`. |
| `-f`, `--format FORMAT` | `text` (default), `mermaid`, `dot` or `json`. |
| `-o`, `--output FILE` | Write to a file instead of stdout. |
| `--print-hash` | Print the graph hash and the tree hash instead of the graph ([Hashes](output-formats.md#hashes)). |
| `-c`, `--config FILE` | Project config. Defaults to `./beehave.yaml` or `./.beehave.yaml` if present. |
| `--package NAME=DIR` | Where `<include ros_pkg="NAME">` finds the package. Repeat for several; wins over `beehave.yaml` and a sourced workspace. |
| `-q`, `--quiet` | Do not print warnings. |

## `beehave stats`

Prints the Phase 1 metrics for one tree: node counts, actions, reduction,
transitions, longest guard and the approximated node types. `--json` prints
the same numbers as JSON.

## `beehave ids`

Lists every node of the instantiated tree (the tree with its subtrees inlined)
with its runtime id, its BT.CPP v4 runtime path, its stable path and, for
actions, its vertex in the graph. Controls, decorators and conditions are
listed too, so an id read from a log can always be found.
See [Node ids and paths](node-ids.md).

| Option | Meaning |
| --- | --- |
| `--scheme SCHEME` | `btcpp-v4` (default): from 1, like BT.CPP v4 UIDs. `preorder`: from 0. |
| `--json` | Print the nodes as JSON (schema `beehave.runtime-ids`, version 1). |

It also takes `-t`, `--py-trees`, `--kwargs`, `-c`, `--package` and `-q`,
like `beehave graph`.

## `beehave diff`

Compares the action graphs of two trees, `OLD` and `NEW` (each a file or a
folder): actions and transitions added, removed, moved or changed, changed
guards, reachability, and a transition score. See
[Comparing two trees](diff.md).

| Option | Meaning |
| --- | --- |
| `-t`, `--tree TREE` | The tree to compare in both. Defaults to the main tree. |
| `-f`, `--format FORMAT` | `text` (default), `markdown` or `json`. |
| `-o`, `--output FILE` | Write to a file instead of stdout. |
| `--exit-code` | Exit with 3 when the graphs differ. |

## `beehave trees`

Lists the trees defined in the files, marking the main one:

```console
$ beehave trees examples/aerial/drone_mission.xml
DroneMission (main)
ReturnToLaunch
```

## py_trees trees

```console
$ beehave graph --py-trees my_robot.trees:create_root -f mermaid
$ beehave graph --py-trees trees/mission.py:create_root -c beehave.yaml
$ beehave graph --py-trees py_trees.demos.dot_graphs:create_tree --kwargs '{"level": "all"}'
```

For `module:function`, the current directory is put first on `sys.path`, as
`python -m` does. For `file.py:function`, the file's directory is, so its
sibling imports work. The `py-trees-render` form `package.module.function` is
accepted too. Run Beehave in the environment of the tree: your virtualenv
active, or your ROS 2 workspace sourced.

## Exit codes

| Code | Meaning |
| --- | --- |
| 0 | Success. Warnings may have been printed. |
| 1 | The input could not be analysed (malformed XML, missing subtree, files that mix BT.CPP v3 and v4, a py_trees factory that raised, bad config…). The reason is printed on stderr. |
| 2 | Wrong command line usage. |
| 3 | `beehave diff --exit-code` found a change. |

## Use in CI

Because output is deterministic, you can commit graphs next to your trees and
fail CI when they drift:

```console
$ beehave graph trees/mission.xml -f mermaid -o docs/mission.mmd -q
$ git diff --exit-code docs/mission.mmd
```
