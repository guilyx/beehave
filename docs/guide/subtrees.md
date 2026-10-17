# Subtrees and includes

Real projects split their trees: a `Dock` subtree reused by several missions,
recoveries in their own file, a package of shared trees. Beehave inlines every
subtree, so the graph shows the actions that really run, wherever they are
defined.

## Subtrees

Every subtree form BehaviorTree.CPP accepts is inlined, with its port
remapping:

| Form | Version | Remapping |
| --- | --- | --- |
| `<SubTree ID="Dock" goal="dock_pose"/>` | v3 | bare key names; `__shared_blackboard="true"` shares every key |
| `<SubTreePlus ID="Dock" goal="{dock_pose}" __autoremap="true"/>` | v3 | `{key}`, literals, and `__autoremap` for every other key |
| `<SubTree ID="Dock" goal="{dock_pose}" _autoremap="true"/>` | v4 | `{key}`, `{=}` (same name), `{@key}` (root blackboard), local literals; `_autoremap` keeps private `_keys` local |
| `<Dock/>` | v3 and v4 | read as a subtree reference, with a warning: BT.CPP itself rejects this short form |

A port inside the subtree shows the key it really reads after remapping. A key
that is not remapped belongs to that use of the subtree and is shown as
`{Dock/goal}`, then `{Dock#2/goal}` for the second use, and so on. In v4, keys
inside scripts (`_skipIf`, `ScriptCondition`…) are remapped the same way. Each
action also records the subtrees it came from (`subtrees` in the JSON output).

A subtree that includes itself, directly or not, is an error, as in BT.CPP.

## Trees in several files

There are three ways a tree reaches a subtree defined in another file, and
Beehave follows all three.

### `<include path="…"/>`

```xml
<include path="subtrees/dock.xml"/>
```

The path is relative to the including file. Includes can include other files,
and each file is read once, so include cycles are harmless.

### `<include ros_pkg="…" path="…"/>`

```xml
<include ros_pkg="my_robot_bt" path="behavior_trees/dock.xml"/>
```

BT.CPP takes `path` inside the package's directory: its share directory on
ROS 2, the `rospack` directory on ROS 1. Beehave looks for the package in this
order, and does not need ROS installed:

1. a directory you name: `packages:` in [`beehave.yaml`](configuration.md), or
   `--package my_robot_bt=src/my_robot_bt` on the command line;
2. `AMENT_PREFIX_PATH`, set by sourcing a ROS 2 workspace: the package's share
   directory, from the ament index;
3. `ROS_PACKAGE_PATH`, set by sourcing a ROS 1 workspace: the folder whose
   `package.xml` has that name.

An installed package usually mirrors its source folder, so pointing a package
at its source works too, without building anything:

```yaml
# beehave.yaml
packages:
  my_robot_bt: src/my_robot_bt
```

As in BT.CPP, an absolute `path` ignores `ros_pkg`, with a warning. Includes in
other forms, such as AutoAPMS's `<include autoapms="…"/>`, are reported and
skipped.

### Trees registered from code

Many applications register every tree file of a folder from code and then
pick a tree by ID: Nav2's `bt_search_directories`, the BehaviorTree.ROS2
samples, `factory.registerBehaviorTreeFromFile()` in a loop. One file then uses
a subtree from another without any `<include>`. Pass the folder:

```console
$ beehave graph behavior_trees/ -t NavigateToPose
```

A folder stands for every `.xml` file directly in it (not in its subfolders),
read in name order. You can mix folders and files, and pass several of each.
Use `-t` to pick the tree when the files do not name a main one.

## When a subtree is missing

```text
beehave: error: main.xml:3: subtree 'Dock' is not defined in the loaded files;
an <include> was not followed, it may be there: main.xml:2: cannot find the ROS
package "my_robot_bt" for <include path="trees/dock.xml">; source its
workspace, or map it with packages: in beehave.yaml or --package my_robot_bt=DIR
```

The error names the includes Beehave could not follow, because the subtree is
usually in one of them. When there is none, pass the file that defines the
subtree too, or its folder.
