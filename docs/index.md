---
title: Beehave
template: home.html
hide:
  - navigation
  - toc
---

<div class="bh-hero" markdown>

<p class="bh-hero__plate bh-label"><img src="assets/brand/mark.svg" alt="" width="24" height="24"> <span>Beehave <span aria-hidden="true">&middot;</span> static analysis for robot behavior trees</span></p>

<p class="bh-hero__wordmark" aria-hidden="true">beehave</p>

<div class="bh-hero__text" markdown>

# The small branch that matters

Beehave reads a [BehaviorTree.CPP](https://www.behaviortree.dev/) tree (v3 or
v4) or a [py_trees](https://github.com/splintered-reality/py_trees) tree and
shows only the actions your robot can take, in order, with the conditions that
lead to each one.

<p class="bh-hero__io bh-label">Behavior tree XML in <span aria-hidden="true">&middot;</span> the small branch that matters out</p>

```console
$ pip install beehave-bt
$ beehave graph mission.xml -f mermaid
```

<p class="bh-hero__actions" markdown>[Get started](guide/getting-started.md){ .md-button .md-button--primary }
[GitHub](https://github.com/guilyx/beehave){ .md-button }</p>

</div>

--8<-- "overrides/partials/home-figure.html"

</div>

## Three questions, one glance

Behavior trees grow fast. Subtrees, fallbacks, reactive sequences and
decorators stack up until nobody can say what the robot does when a step fails
halfway through a task, whether it flies, drives or grasps. Beehave answers:

<div class="bh-questions" markdown>

1. **Which actions exist** in this tree?
2. **What has to be true** for each one to run?
3. **What runs next** on success, and what runs next on failure?

</div>

## Before and after

A 22-node drone mission becomes 10 actions. Control nodes become arrows,
conditions become arrow labels, subtrees are inlined, retries become notes.

<figure class="bh-figure" markdown>
<figcaption class="bh-label"><span>Fig. 2</span> A drone survey mission: 22 nodes in, 10 actions out</figcaption>

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

</figure>

"What if the emergency landing fails?" takes one arrow to answer, and it shows
a gap: `LandNow` fails over to `Arm`, so the drone would start the mission
again. The same works for [mobile robots and manipulators](guide/examples.md).

## Where to go next

<div class="grid cards" markdown>

- **[Getting started](guide/getting-started.md)**

    Install, run your first graph, read the output.

- **[Examples](guide/examples.md)**

    A drone mission, a mobile robot navigating with recovery, and a
    pick-and-place arm, each in BT.CPP v3, v4 and py_trees.

- **[Formats](guide/formats.md)**

    BehaviorTree.CPP v3 and v4, `SKIPPED` and scripts, and py_trees.

- **[Design](design/index.md)**

    The pipeline, the Phase 1 specification, the roadmap and every design
    decision.

- **[Research](research/index.md)**

    BehaviorTree.CPP semantics checked against the source, prior art and the
    literature.

- **[Phase 1 results](design/phase-1-results.md)**

    The metrics on public BT.CPP, Groot and Nav2 trees.

</div>

!!! note "Not the Godot addon"
    This Beehave is a static analysis tool for robot behavior trees
    (BehaviorTree.CPP, py_trees, ROS 2, Nav2). It is unrelated to the Beehave
    behavior tree addon for the Godot game engine.
