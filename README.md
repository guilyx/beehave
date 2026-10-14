<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset=".branding/logo/lockup-horizontal-dark.svg">
    <img alt="Beehave" src=".branding/logo/lockup-horizontal.svg" width="360">
  </picture>
</p>

<p align="center">
  <b>The small branch that matters.</b><br>
  Beehave reads a BehaviorTree.CPP tree and shows only the actions your robot
  can take, in order, with the conditions that lead to each one.
</p>

<p align="center">
  <a href="https://github.com/guilyx/beehave/actions/workflows/ci.yml"><img alt="CI" src="https://github.com/guilyx/beehave/actions/workflows/ci.yml/badge.svg"></a>
  <a href="https://guilyx.github.io/beehave/"><img alt="Docs" src="https://img.shields.io/badge/docs-guilyx.github.io%2Fbeehave-1b1813"></a>
  <img alt="Python 3.10+" src="https://img.shields.io/badge/python-3.10%2B-1b1813">
  <a href="LICENSE"><img alt="License: Apache-2.0" src="https://img.shields.io/badge/license-Apache--2.0-1b1813"></a>
  <img alt="Status: alpha" src="https://img.shields.io/badge/status-alpha%20·%20phase%201-fcc50e">
</p>

---

> **Not the Godot addon.** This Beehave is a static analysis tool for robot
> behavior trees written for [BehaviorTree.CPP](https://www.behaviortree.dev/)
> (ROS 2, Nav2, drones). It is unrelated to the Beehave addon for the Godot game
> engine.

## Why

Behavior trees grow fast. Subtrees, fallbacks, reactive sequences and
decorators stack up until nobody can say *what the drone actually does if the
battery drops halfway to the zone* without tracing the XML by hand.

Beehave answers three questions at a glance:

- **Which actions exist** in this tree?
- **What has to be true** for each one to run?
- **What runs next** on success, and what runs next on failure?

## What it does

A 20-node landing tree in, an 8-action graph out. Control nodes become arrows,
conditions become arrow labels, subtrees are inlined, retries become notes.

```console
$ beehave graph landing.xml -f mermaid
```

```mermaid
flowchart TD
    start(("START"))
    a1["EmergencyLand"]
    a2["FlightDefaults"]
    a3["GoToZone<br/><small>retry ×3</small>"]
    a4["ResolveHome"]
    a5["FlyToHome"]
    a6["ResolveSafe"]
    a7["FlyToSafe"]
    a8["Land"]
    success(["SUCCESS"])
    failure(["FAILURE"])
    start -->|"Emergency"| a1
    start -->|"not Emergency"| a2
    a1 -->|"success"| success
    a1 -.->|"failure"| a2
    a2 -->|"success and BatteryOK"| a3
    a2 -->|"success and not BatteryOK"| a4
    a2 -.->|"failure"| failure
    a3 -->|"success"| success
    a3 -.->|"failure"| a4
    a4 -->|"success"| a5
    a4 -.->|"failure"| failure
    a5 -->|"success"| a8
    a5 -.->|"failure"| a6
    a6 -->|"success"| a7
    a6 -.->|"failure"| failure
    a7 -->|"success"| a8
    a7 -.->|"failure"| failure
    a8 -->|"success"| success
    a8 -.->|"failure"| failure
```

"What if `GoToZone` fails?" now takes one arrow to answer. And the gap jumps
out: `FlyToSafe` has no failure path.

## Install

```console
$ pip install beehave-bt        # or: uv tool install beehave-bt
```

The PyPI package is `beehave-bt`; the command and the module are `beehave`.
Python 3.10+ (ROS 2 Humble and newer).

## Use

```console
$ beehave graph mission.xml                       # transitions as text
$ beehave graph mission.xml -f mermaid -o mission.mmd
$ beehave graph mission.xml -f dot | dot -Tsvg > mission.svg
$ beehave graph mission.xml -f json               # for other tools
$ beehave stats mission.xml                       # size, reduction, breakage
$ beehave trees mission.xml                       # list the trees
```

```python
import beehave

result = beehave.analyze("mission.xml")
print(beehave.to_mermaid(result.graph))
print(result.stats.reduction)
```

Custom nodes are actions unless the XML or a small `beehave.yaml` says they
are conditions:

```yaml
conditions: [BatteryOK, IsEmergency]
```

## Status

Beehave is in **Phase 1** of a four-phase plan.

| Phase | What | Status |
| --- | --- | --- |
| 1. Action graph | Parse BT.CPP v3, flatten subtrees, walk, render | **in progress** |
| 2. Guards and metrics | Simplified guards, exact Reactive/Retry/Parallel, gap report, BT.CPP v4 | planned |
| 3. Operator view | Operator labels, phase view, JSON for ground-control UIs, live status | planned |
| 4. LTL checks | Temporal-logic safety rules and model checking | optional |

Nodes Phase 1 cannot model exactly (reactive nodes, loops, Parallel, unknown
custom nodes) are approximated **and always reported**, never silently. See
the [node support table](https://guilyx.github.io/beehave/design/phase-1/#node-support).

## Learn more

- 📖 [Documentation](https://guilyx.github.io/beehave/)
- 🧭 [Design: architecture, Phase 1 spec, ADRs](https://guilyx.github.io/beehave/design/)
- 🔬 [Research: BT.CPP semantics, prior art, literature](https://guilyx.github.io/beehave/research/)
- 🗺️ [Roadmap](https://guilyx.github.io/beehave/design/roadmap/)

## Contributing

Contributions are welcome: bug reports with a minimal tree, new node rules,
docs. We work test-first, and every walk rule is checked against a reference
interpreter with property-based tests. Start with
[CONTRIBUTING.md](CONTRIBUTING.md) and the
[good first issues](https://github.com/guilyx/beehave/labels/good%20first%20issue).

Please follow the [Code of Conduct](CODE_OF_CONDUCT.md). Report security
issues privately, as described in [SECURITY.md](SECURITY.md).

## License

[Apache-2.0](LICENSE). The brand (logo, palette, type, graph style) is
documented in [`.branding/`](.branding/README.md); its assets have their own
[license](.branding/LICENSE.md). If you use Beehave in research, see
[CITATION.cff](CITATION.cff).
