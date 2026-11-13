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
nodes:
  PipelineSequence: pipeline_sequence
bookkeeping:
  - LogMessage
packages:
  my_robot_bt: src/my_robot_bt
```

| Key | Meaning |
| --- | --- |
| `conditions` | Custom node types to treat as conditions. They become guards on edges, not boxes. |
| `actions` | Custom node types to treat as actions, even if the XML declares them as conditions. |
| `nodes` | Custom controls and decorators, and the [preset](#presets) each behaves like. |
| `bookkeeping` | Actions that do not act on the world, left out of the graph ([Bookkeeping actions](#bookkeeping-actions)). |
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
in two of `conditions`, `actions`, `nodes` and `bookkeeping`.

## Where Beehave looks

1. The file given with `-c` / `--config`.
2. Otherwise `beehave.yaml`, then `.beehave.yaml`, in the current directory.

From Python, pass a `beehave.Config` or use `beehave.load_config(path)`.

## How a node is classified

For each custom node type in a BT.CPP file, the strongest signal wins:

1. this config file (`conditions`, `actions`, `nodes` or `bookkeeping`);
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

## Presets

Beehave does not know what a project's own control or decorator does. It
walks an unknown control like a `Sequence` and an unknown decorator as
transparent, and reports both. When your node behaves like one Beehave knows,
say so under `nodes`, and it is walked by that rule instead:

```yaml
nodes:
  PipelineSequence: pipeline_sequence      # short form
  KeepTrying:
    behaves_like: until_success            # long form
  RepeatUntilDone:
    behaves_like: loop_until_flag
    flag_port: done                        # <RepeatUntilDone done="{mission_over}">
```

A preset fixes the node's kind and how many children it may have; a node
with the wrong number of children is an error. Nodes listed under `nodes`
count as the project's own everywhere, like those under `conditions` and
`actions`: a BT.CPP v3 project may have its own `ParallelAll`, and declaring
it keeps the file from being read as v4. A preset for a built-in node of the
file's BT.CPP version is ignored with a warning (`preset-ignored`), since BT.CPP
cannot register a second node of that name.

For py_trees, `nodes` names classes like `conditions` does, and applies to
user composites and decorators.

### Built-in equivalents

| Preset | Walked like | Exact |
| --- | --- | --- |
| `sequence` | `Sequence` | yes |
| `sequence_with_memory` | `SequenceWithMemory` (`SequenceStar` in v3) | yes |
| `fallback` | `Fallback` | yes |
| `if_then_else` | `IfThenElse`, 2 or 3 children | yes |
| `try_catch` | `TryCatch`, 2 or more children | yes |
| `inverter`, `force_success`, `force_failure` | the decorator of that name | yes |
| `pass_through` | a decorator that returns its child's result | yes |
| `reactive_sequence`, `reactive_fallback` | `ReactiveSequence`, `ReactiveFallback` | reported, like the built-ins |
| `while_do_else` | `WhileDoElse`, 2 or 3 children | reported |
| `parallel`, `parallel_all` | `Parallel`, `ParallelAll` | reported |
| `retry`, `repeat`, `keep_running_until_failure`, `timeout`, `run_once` | the decorator of that name | reported |
| `pipeline_sequence` | Nav2 `PipelineSequence`: a `Sequence` whose earlier children are ticked again while a later one runs | reported |
| `round_robin` | Nav2 `RoundRobin`: a `Fallback` that starts after the child that last succeeded | reported |

### Generic patterns

| Preset | Behaviour | How it is walked |
| --- | --- | --- |
| `until_success` (also `keep_running_until_success`) | Ticks its child again after each failure, until it succeeds. It never fails. | A failure of the child has no edge. When the child can run an action, the edge back to it is missing and reported. |
| `poll_until_success` | The same, for a child that checks something: it waits until the check holds. | Exact when the child only checks: the next action is guarded by the check. |
| `loop_until_flag` | Before each tick of its child, checks a blackboard flag: when it is set, the node exits; a failed child fails the node. | The exit is an edge guarded by the flag; when the child can run an action, the edge back to it is missing and reported. |
| `parallel_first_success` | Runs its children at the same time; succeeds when one succeeds, fails when all have failed. | Like a `Fallback`, as if the children ran one after another, and reported. |

`loop_until_flag` takes two options. `flag_port` (default `flag`) is the port
that holds the flag, written `{key}`; the flag reads like the BT.CPP script
`key`, through subtree remapping. `exit` (`success`, the default, or
`failure`) is what the node returns once the flag is set.

```yaml
nodes:
  AbortWhen:
    behaves_like: loop_until_flag
    flag_port: abort
    exit: failure
```

The loops cannot be drawn until the graph has cycles (FD5 in the
[roadmap](../design/roadmap.md#foundations-track)), so their walk stops where
the child would start again, and says so. It never draws an edge that cannot
happen: an `until_success` child that fails has no failure edge at all.

## Bookkeeping actions

Some actions do not act on the world: they log a message, publish a status,
or copy a value on the blackboard. As boxes they get in the way of the
question the graph answers, "what runs after this action?". List them under
`bookkeeping` and they are left out, with the edges through them joined up:

```yaml
bookkeeping:
  - LogMessage            # may fail
  - SaveCheckpoint
# or, to say which never fail:
bookkeeping:
  LogMessage: {never_fails: true}
  SaveCheckpoint: {}
```

```text
# <Sequence><Arm/><LogMessage/><TakeOff/></Sequence>, LogMessage may fail:
START --> Arm
Arm --[success and LogMessage succeeded]--> TakeOff
Arm --[success and LogMessage failed]--> FAILURE
Arm --[failure]--> FAILURE
...
# with never_fails: true
Arm --[success]--> TakeOff
```

A bookkeeping action that may fail is not dropped silently: its result
becomes a guard on the edges that go through it (`LogMessage succeeded`,
`LogMessage failed`), one condition per node. One that never fails, or whose
result does not matter (under a `ForceSuccess`, say), adds no guard.

Beehave does not know what a bookkeeping action writes, so a check made
before it does not decide the same check made after it, as with `Script` and
`SetBlackboard`. A bookkeeping node keeps its [runtime id](node-ids.md); it is
just not a vertex. Only leaves can be bookkeeping, and a built-in node listed
here is ignored with a warning (`bookkeeping-ignored`). For py_trees,
`bookkeeping` names classes like `conditions` does.
