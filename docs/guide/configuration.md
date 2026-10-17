# Configuration

Beehave works on any tree without configuration. One optional file per
project, `beehave.yaml`, tells it what the XML cannot.

```yaml
# beehave.yaml
conditions:
  - BatteryOK
  - IsEmergency
actions:
  - Probe
packages:
  my_robot_bt: src/my_robot_bt
```

| Key | Meaning |
| --- | --- |
| `conditions` | Custom node types to treat as conditions. They become guards on edges, not boxes. |
| `actions` | Custom node types to treat as actions, even if the XML declares them as conditions. |
| `packages` | Where `<include ros_pkg="…">` finds each ROS package, relative to this file. It wins over a sourced workspace. See [Subtrees and includes](subtrees.md). |

For py_trees, a node type is a behaviour class, named by `__name__` (`IsAt`)
or by `module.QualName` (`my_robot.checks.IsAt`). Naming a base class covers
every class derived from it, and the nearest class in the hierarchy decides:

```yaml
# Every behaviour derived from Check is a condition, except IsCharging.
conditions:
  - Check
actions:
  - IsCharging
```

The config only classifies nodes. It never makes Beehave import or run
anything: a py_trees tree is only read when you pass `--py-trees`.

Unknown keys are an error, so a typo does not go unnoticed. A node cannot be
in both lists.

## Where Beehave looks

1. The file given with `-c` / `--config`.
2. Otherwise `beehave.yaml`, then `.beehave.yaml`, in the current directory.

From Python, pass a `beehave.Config` or use `beehave.load_config(path)`.

## How a node is classified

For each custom node type in a BT.CPP file, the strongest signal wins:

1. this config file;
2. the explicit XML form, such as `<Condition ID="BatteryOK"/>`;
3. the `<TreeNodesModel>` section of the tree files;
4. its shape: no child means action, one child decorator, several control.

Built-in BT.CPP nodes (`Sequence`, `Inverter`, …) are always classified by
Beehave itself. So are the py_trees built-ins, except the stand-ins for real
work (`StatusQueue`, `TickCounter`, `SuccessEveryN`…), which the config can
reclassify. py_trees has no condition type, so a user behaviour is an action
unless the config says otherwise.

## Conditions in disguise

Some projects register nodes as actions that only check something: they
never change the world and only return success or failure. Listing them under
`conditions` turns them into guards, which usually makes the graph much
smaller and easier to read.
