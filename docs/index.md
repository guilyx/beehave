---
title: Beehave
template: home.html
hide:
  - navigation
  - toc
---

<div class="bh-hero" markdown>

<p class="bh-hero__plate bh-label"><img src="assets/brand/mark.svg" alt="" width="24" height="24"> <span>Beehave <span aria-hidden="true">&middot;</span> static analysis for BehaviorTree.CPP</span></p>

<p class="bh-hero__wordmark" aria-hidden="true">beehave</p>

<div class="bh-hero__text" markdown>

# The small branch that matters

Beehave reads a [BehaviorTree.CPP](https://www.behaviortree.dev/) tree and
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
decorators stack up until nobody can say what the robot does if the battery
drops halfway to the zone. Beehave answers:

<div class="bh-questions" markdown>

1. **Which actions exist** in this tree?
2. **What has to be true** for each one to run?
3. **What runs next** on success, and what runs next on failure?

</div>

## Before and after

A 20-node landing tree becomes 8 actions. Control nodes become arrows,
conditions become arrow labels, subtrees are inlined, retries become notes.

<figure class="bh-figure" markdown>
<figcaption class="bh-label"><span>Fig. 2</span> The landing tree: 20 nodes in, 8 actions out</figcaption>

```mermaid
---
config:
  theme: base
  themeVariables:
    edgeLabelBackground: "#f5f0e9"
    lineColor: "#1b1813"
---
%% Beehave action graph: Mission (btcpp-v3)
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
    classDef start fill:#1b1813,stroke:#1b1813,stroke-width:1.5px,color:#f5f0e9
    classDef action fill:#fdfbf9,stroke:#1b1813,stroke-width:1.5px,color:#1b1813
    classDef success fill:#107550,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    classDef failure fill:#b93917,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    class start start
    class a1,a2,a3,a4,a5,a6,a7,a8 action
    class success success
    class failure failure
    linkStyle 0,1 stroke:#1b1813,stroke-width:1.75px
    linkStyle 2,4,5,7,9,11,13,15,17 stroke:#107550,stroke-width:1.75px
    linkStyle 3,6,8,10,12,14,16,18 stroke:#b93917,stroke-width:1.75px,stroke-dasharray:7 4
```

</figure>

"What if `GoToZone` fails?" takes one arrow to answer. The gap is visible too:
`FlyToSafe` has no failure path.

## Where to go next

<div class="grid cards" markdown>

- **[Getting started](guide/getting-started.md)**

    Install, run your first graph, read the output.

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
    (BehaviorTree.CPP, ROS 2, Nav2). It is unrelated to the Beehave behavior
    tree addon for the Godot game engine.
