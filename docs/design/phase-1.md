# Phase 1: the action graph

**Status:** in progress · **Format:** BehaviorTree.CPP v3 · **Output:** action graph

## Problem

Behavior trees grow fast. Subtrees, fallbacks, reactive sequences and
decorators stack up until nobody can say what the robot actually does if the
battery drops halfway through a mission without tracing the XML by hand.

Phase 1 answers three questions for any BT.CPP v3 tree, at a glance:

1. Which actions exist in this tree?
2. What has to be true for each one to run?
3. What runs next on success, and what runs next on failure?

## Scope

**In scope**

- Static analysis of BT.CPP v3 XML, including `<include>`,
  `<TreeNodesModel>`, `SubTree` and `SubTreePlus` with `__autoremap`.
- An action graph: one box per action, one arrow per transition, the raw
  guard on each arrow.
- Text, Mermaid, Graphviz DOT and JSON output.
- Works on any tree with no per-tree configuration. One optional project
  file lists custom nodes that are conditions.
- Pilot metrics: size, reduction, longest raw guard, breakage.

**Not in scope for Phase 1**

- Simplifying guards, merging edges (Phase 2).
- Exact rules for reactive nodes, loops and Parallel (Phase 2). Phase 1
  approximates them and says so.
- BT.CPP v4 (Phase 2). Phase 1 detects v4 and refuses it.
- Operator labels and the C2 view (Phase 3).
- Log replay, temporal logic, model checking (later, optional).
- Editing or generating trees.

## Before and after

The landing tree from the design plan. Node names are illustrative.

**Before:** 20 nodes in the flattened tree, 8 of them actions.

```mermaid
flowchart TD
    RF[ReactiveFallback] --> RS[ReactiveSequence]
    RF --> S1[Sequence]
    RS --> E{{Emergency?}}
    RS --> EL[EmergencyLand]
    S1 --> FD[FlightDefaults]
    S1 --> F1[Fallback]
    F1 --> S2[Sequence]
    F1 --> RH[/"SubTree: ReturnHome"/]
    S2 --> B{{BatteryOK?}}
    S2 --> R["Retry ×3"]
    R --> G[GoToZone]
    RH --> S3[Sequence]
    S3 --> RHo[ResolveHome]
    S3 --> F2[Fallback]
    S3 --> L[Land]
    F2 --> FH[FlyToHome]
    F2 --> S4[Sequence]
    S4 --> RSa[ResolveSafe]
    S4 --> FS[FlyToSafe]
```

**After:** `beehave graph landing.xml -f mermaid`

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

What changed:

- **Control nodes are gone.** Sequences, Fallbacks and the ReactiveFallback
  became arrows.
- **Conditions became arrow labels.** `BatteryOK` is a guard on two edges.
- **Retry folded into the action.** It is a note on `GoToZone`.
- **Subtrees are inlined.** `ReturnHome` is gone as a node; its actions
  joined the graph.
- **The gap is visible.** `FlyToSafe` fails straight to `FAILURE`: there is no
  failure path. In Phase 2 the gap report will flag this automatically.

The reactive emergency branch is walked like a plain Fallback in Phase 1, so
the graph shows `Emergency` only at the start. Phase 2 adds a preemption edge
from every action to `EmergencyLand`. Until then, `beehave` prints a warning
for each reactive node so the reader knows.

## The walk

The walk is a **continuation-passing compilation** of the tree.

Each node is compiled with two continuations:

- `s`: where execution goes when the node **succeeds**;
- `f`: where execution goes when the node **fails**.

Compiling a node returns its **entry**: what runs first when it is ticked. An
entry is an action, a terminal (`SUCCESS`, `FAILURE`), or a **branch point**
on a condition.

| Node | Rule |
| --- | --- |
| Action | Record edges `action → s` on success, `action → f` on failure. Entry is the action. |
| Condition | Entry is a branch: "if it holds → `s`, else → `f`". |
| `Sequence(c₁ … cₙ)` | Compile right to left: `cₙ` with `(s, f)`, then each `cᵢ` with `(entry(cᵢ₊₁), f)`. Entry is `entry(c₁)`. |
| `Fallback(c₁ … cₙ)` | Compile right to left: `cₙ` with `(s, f)`, then each `cᵢ` with `(s, entry(cᵢ₊₁))`. |
| `Inverter(c)` | Compile `c` with `(f, s)`. |
| `ForceSuccess(c)` | Compile `c` with `(s, s)`. |
| `ForceFailure(c)` | Compile `c` with `(f, f)`. |
| `IfThenElse(c, t, e)` | Compile `c` with `(entry(t), entry(e))`; without `e`, `(entry(t), f)`. |
| `Switch(v; k₁ … kₙ; c₁ … cₙ, d)` | A chain of branches on `v == kᵢ`, default `d`. |
| `BlackboardCheck(a, b)(c)` | A branch on `a == b`; mismatch goes to `s` or `f` per `return_on_mismatch`. |
| `AlwaysSuccess`, `SetBlackboard` | Entry is `s` (no box). |
| `AlwaysFailure` | Entry is `f` (no box). |
| Subtree | Compile its inlined body with `(s, f)`. |

The tree's root is compiled with `(SUCCESS, FAILURE)`. Its entry gives the
edges out of `START`.

Finally, each edge target is **expanded**: branch points are followed until a
real action or terminal is reached, and the conditions passed on the way
become the edge's guard. Two things keep guards honest:

- A path that requires a condition to hold and not hold is impossible, so it
  is dropped.
- A condition checked twice on one path appears once.

Both assume a condition gives the same answer when checked twice in the same
tick with no action in between. That is how conditions are meant to be
written in BT.CPP.

The expansion is capped (1024 transitions per action outcome by default). A
tree that hits the cap gets a `too-many-paths` diagnostic rather than an
endless run.

### Why this is correct

`tests/property/test_walk_matches_execution.py` generates random trees from
the node types above, random values for each condition, and random outcomes
for each action. A small reference interpreter runs the tree. Following the
graph with the same values must visit the same actions in the same order and
end with the same result, with **exactly one** matching edge at every step.
That one check proves the guards are complete and mutually exclusive.

## Node support

| Node (BT.CPP v3) | Phase 1 | Notes |
| --- | --- | --- |
| `Sequence`, `SequenceStar` | exact | Memory does not change a single static walk. |
| `Fallback` | exact | |
| `Inverter`, `ForceSuccess`, `ForceFailure` | exact | |
| `IfThenElse` | exact | 2 or 3 children. |
| `Switch2` … `Switch6` | exact | Guards like `mode == AUTO`. |
| `BlackboardCheckInt/Double/String` | exact | Guard `a == b`; `RUNNING` on mismatch is approximated. |
| `AlwaysSuccess`, `AlwaysFailure`, `SetBlackboard` | exact | Not shown as boxes. |
| `Timeout`, `Delay` | exact | Transparent: they do not change which action runs next. |
| `SubTree`, `SubTreePlus` | exact | Inlined with remapping. |
| `ReactiveSequence`, `ReactiveFallback` | approximated | Walked like the plain version; no preemption edges yet. |
| `RetryUntilSuccessful`, `Repeat` | approximated | Loop folded into a note (`retry ×3`). |
| `KeepRunningUntilFailure` | approximated | Transparent; loop not shown. |
| `WhileDoElse` | approximated | Walked like `IfThenElse`. |
| `Parallel` | approximated | Children shown as if run one after another. |
| `ManualSelector` | approximated | Walked like a `Fallback`. |
| Custom action / condition | exact | Action unless configured or declared as a condition. |
| Custom decorator | approximated | Treated as transparent. |
| Custom control | approximated | Walked like a `Sequence`. |

Every approximated node produces a diagnostic with its location. The
`approximated` line of `beehave stats` is the plan's **breakage** metric: what
Phase 2 has to fix.

## Configuration

Beehave works without configuration. A project can add a `beehave.yaml`:

```yaml
conditions:   # custom nodes that only check something
  - BatteryOK
  - IsEmergency
actions:      # force a node to be an action
  - Probe
```

The config is the strongest signal; it overrides `TreeNodesModel` and the
explicit XML form. It is how to fix "conditions in disguise".

## Pilot metrics

`beehave stats tree.xml` prints the Phase 1 numbers:

| Metric | Meaning |
| --- | --- |
| nodes | Nodes in the flattened tree, by kind. |
| actions | Actions shown in the graph. |
| reduction | `1 - actions / nodes`: how much smaller the view is. |
| transitions | Edges in the graph. |
| longest guard | Terms in the longest guard, before simplification. |
| approximated | Node types Phase 1 could not model exactly (breakage). |

For the landing tree: 20 nodes, 8 actions, 60% reduction, 19 transitions,
longest guard 1 term, 3 approximated nodes.

## Exit criteria

Phase 1 is done when:

- [x] The tool produces a graph for the pilot trees, with the metrics recorded.
- [ ] It runs on a set of public trees (Nav2, BT.CPP examples) without manual
      edits, and the breakage list is recorded.
- [ ] Someone who did not write a tree can answer "what happens if X fails?"
      from the graph alone.

When the last box is ticked, we decide whether to carry on to Phase 2 as
planned.
