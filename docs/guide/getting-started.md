# Getting started

## Install

```console
$ pip install beehave-bt
```

Or with [uv](https://docs.astral.sh/uv/):

```console
$ uv tool install beehave-bt
```

The package is called `beehave-bt` on PyPI. The command and the Python module
are both `beehave`. Beehave needs Python 3.10 or newer, which includes ROS 2
Humble.

!!! note "Not the Godot addon"
    This Beehave reads BehaviorTree.CPP trees for robots. It is not related to
    the Beehave behavior tree addon for the Godot game engine.

## Your first graph

Take a tree file, for example the drone mission from
[the examples](examples.md)
([`drone_mission.xml`](https://github.com/guilyx/beehave/blob/main/examples/aerial/drone_mission.xml)):

```console
$ beehave graph examples/aerial/drone_mission.xml
START --[IsBatteryCritical]--> LandNow
START --[not IsBatteryCritical]--> Arm
LandNow --[success]--> SUCCESS
LandNow --[failure]--> Arm
Arm --[success]--> TakeOff
Arm --[failure]--> FAILURE
TakeOff --[success and IsBatteryOK]--> FlyToWaypoint
TakeOff --[success and not IsBatteryOK]--> FlyHome
TakeOff --[failure]--> FAILURE
...
```

Each line is one transition: when the action on the left ends with that
outcome and the guard holds, the action on the right runs next.

On stderr, Beehave also lists the nodes it could only approximate:

```text
beehave: examples/aerial/drone_mission.xml:11: warning: ReactiveFallback
"mission_with_failsafe": walked like a Fallback; its conditions are re-checked every
tick, but preemption edges are not shown yet [approximated]
```

## A picture instead

```console
$ beehave graph examples/aerial/drone_mission.xml -f mermaid -o mission.mmd
```

Paste the result into any Markdown file on GitHub, or into
[mermaid.live](https://mermaid.live). For Graphviz:

```console
$ beehave graph examples/aerial/drone_mission.xml -f dot | dot -Tsvg > mission.svg
```

## How much simpler is it?

```console
$ beehave stats examples/aerial/drone_mission.xml
tree           DroneMission (btcpp-v3)
nodes          22 (7 control, 2 decorator, 2 condition, 10 action, 1 subtree)
actions        10
reduction      55% (22 nodes -> 10 actions)
transitions    23
longest guard  1 term (not simplified)
approximated   ReactiveFallback ×1, ReactiveSequence ×1, RetryUntilSuccessful ×1
```

## Custom conditions

Beehave treats every custom node as an action unless it knows better. It
knows better when:

- the XML uses the explicit form `<Condition ID="IsBatteryOK"/>`, or
- the file declares it in `<TreeNodesModel>`, or
- your project lists it in a `beehave.yaml` file:

```yaml
conditions:
  - IsBatteryOK
  - IsObjectGrasped
```

See [Configuration](configuration.md).

## Next steps

- [Command line](cli.md): every option.
- [Output formats](output-formats.md): what the JSON contains.
- [Python API](python-api.md): use Beehave from code.
- [Phase 1 design](../design/phase-1.md): how the graph is computed.
