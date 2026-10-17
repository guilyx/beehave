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
> (ROS 2, Nav2: drones, mobile robots, manipulators). It is unrelated to the
> Beehave addon for the Godot game engine.

## Why

Behavior trees grow fast. Subtrees, fallbacks, reactive sequences and
decorators stack up until nobody can say *what the robot actually does when a
step fails halfway through a task*, whether it flies, drives or grasps,
without tracing the XML by hand.

Beehave answers three questions at a glance:

- **Which actions exist** in this tree?
- **What has to be true** for each one to run?
- **What runs next** on success, and what runs next on failure?

## What it does

A 22-node drone mission in, a 10-action graph out. Control nodes become
arrows, conditions become arrow labels, subtrees are inlined, retries become
notes.

```console
$ beehave graph examples/aerial/drone_mission.xml -f mermaid
```

```mermaid
---
config:
  theme: base
  themeVariables:
    edgeLabelBackground: "#f5f0e9"
    lineColor: "#1b1813"
---
%% Beehave action graph: DroneMission (btcpp-v3)
flowchart TD
    start(("START"))
    a1["LandNow"]
    a2["Arm"]
    a3["TakeOff"]
    a4["FlyToWaypoint<br/><small>retry ×3</small>"]
    a5["CaptureImage"]
    a6["FlyHome"]
    a7["FindLandingSpot"]
    a8["FlyToLandingSpot"]
    a9["Land"]
    a10["Disarm"]
    success(["SUCCESS"])
    failure(["FAILURE"])
    start -->|"IsBatteryCritical"| a1
    start -->|"not IsBatteryCritical"| a2
    a1 -->|"success"| success
    a1 -.->|"failure"| a2
    a2 -->|"success"| a3
    a2 -.->|"failure"| failure
    a3 -->|"success and IsBatteryOK"| a4
    a3 -->|"success and not IsBatteryOK"| a6
    a3 -.->|"failure"| failure
    a4 -->|"success"| a5
    a4 -.->|"failure"| a6
    a5 -->|"success"| a6
    a5 -.->|"failure"| a6
    a6 -->|"success"| a9
    a6 -.->|"failure"| a7
    a7 -->|"success"| a8
    a7 -.->|"failure"| failure
    a8 -->|"success"| a9
    a8 -.->|"failure"| failure
    a9 -->|"success"| a10
    a9 -.->|"failure"| failure
    a10 -->|"success"| success
    a10 -.->|"failure"| failure
    classDef start fill:#1b1813,stroke:#1b1813,stroke-width:1.5px,color:#f5f0e9
    classDef action fill:#fdfbf9,stroke:#1b1813,stroke-width:1.5px,color:#1b1813
    classDef success fill:#107550,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    classDef failure fill:#b93917,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    class start start
    class a1,a2,a3,a4,a5,a6,a7,a8,a9,a10 action
    class success success
    class failure failure
    linkStyle 0,1 stroke:#1b1813,stroke-width:1.75px
    linkStyle 2,4,6,7,9,11,13,15,17,19,21 stroke:#107550,stroke-width:1.75px
    linkStyle 3,5,8,10,12,14,16,18,20,22 stroke:#b93917,stroke-width:1.75px,stroke-dasharray:7 4
```

"What if the emergency landing fails?" now takes one arrow to answer, and the
answer is a gap: `LandNow` fails over to `Arm`, so the drone would start the
mission again.

The same works for any robot. The [`examples/`](examples/) folder has three
generic trees:

| Example | Robot | Tree → graph |
| --- | --- | --- |
| [Drone survey mission](examples/aerial/drone_mission.xml) | Multirotor | 22 nodes → 10 actions |
| [Navigate to a goal, with recovery and docking](examples/mobile/navigate_to_goal.xml) | Mobile base | 23 nodes → 11 actions |
| [Pick and place](examples/manipulation/pick_and_place.xml) | Arm and gripper | 24 nodes → 13 actions |

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

Beehave moves along two tracks ([roadmap](https://guilyx.github.io/beehave/design/roadmap/)).

**Phases** — what the graph says:

| Phase | What | Status |
| --- | --- | --- |
| 1. Action graph | Parse, flatten subtrees, walk, render | **done**, readability gate open |
| 2. Guards and metrics | Simplified guards, exact Reactive/Retry/Parallel, gap report | planned |
| 3. Operator view | Operator labels, phase view, JSON for ground-control UIs, live status | planned |
| 4. LTL checks | Temporal-logic safety rules and model checking | optional |

**Formats** — what Beehave reads:

| Format | Status |
| --- | --- |
| BehaviorTree.CPP v3 | **supported** |
| BehaviorTree.CPP v4 | **in progress** |
| py_trees | **in progress** |
| Node presets (Nav2 first) | planned |

Nodes Beehave cannot model exactly yet (reactive nodes, loops, Parallel,
unknown custom nodes) are approximated **and always reported**, never
silently. See the
[node support table](https://guilyx.github.io/beehave/design/phase-1/#node-support).

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
