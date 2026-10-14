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

Take a tree file, for example the landing tree used throughout these docs
([`landing.xml`](https://github.com/guilyx/beehave/blob/main/tests/fixtures/trees/landing.xml)):

```console
$ beehave graph landing.xml
START --[Emergency]--> EmergencyLand
START --[not Emergency]--> FlightDefaults
EmergencyLand --[success]--> SUCCESS
EmergencyLand --[failure]--> FlightDefaults
FlightDefaults --[success and BatteryOK]--> GoToZone
FlightDefaults --[success and not BatteryOK]--> ResolveHome
FlightDefaults --[failure]--> FAILURE
GoToZone --[success]--> SUCCESS
GoToZone --[failure]--> ResolveHome
...
```

Each line is one transition: when the action on the left ends with that
outcome and the guard holds, the action on the right runs next.

On stderr, Beehave also lists the nodes it could only approximate:

```text
beehave: landing.xml:8: warning: ReactiveFallback: walked like a Fallback; its
conditions are re-checked every tick, but preemption edges are not shown yet [approximated]
```

## A picture instead

```console
$ beehave graph landing.xml -f mermaid -o landing.mmd
```

Paste the result into any Markdown file on GitHub, or into
[mermaid.live](https://mermaid.live). For Graphviz:

```console
$ beehave graph landing.xml -f dot | dot -Tsvg > landing.svg
```

## How much simpler is it?

```console
$ beehave stats landing.xml
tree           Mission (btcpp-v3)
nodes          20 (8 control, 1 decorator, 2 condition, 8 action, 1 subtree)
actions        8
reduction      60% (20 nodes -> 8 actions)
transitions    19
longest guard  1 term (not simplified)
approximated   ReactiveFallback ×1, ReactiveSequence ×1, RetryUntilSuccessful ×1
```

## Custom conditions

Beehave treats every custom node as an action unless it knows better. It
knows better when:

- the XML uses the explicit form `<Condition ID="BatteryOK"/>`, or
- the file declares it in `<TreeNodesModel>`, or
- your project lists it in a `beehave.yaml` file:

```yaml
conditions:
  - BatteryOK
  - IsEmergency
```

See [Configuration](configuration.md).

## Next steps

- [Command line](cli.md): every option.
- [Output formats](output-formats.md): what the JSON contains.
- [Python API](python-api.md): use Beehave from code.
- [Phase 1 design](../design/phase-1.md): how the graph is computed.
