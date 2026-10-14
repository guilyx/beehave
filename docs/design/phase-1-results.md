# Phase 1 results on public trees

The design plan asks Phase 1 to run on real trees and record the metrics. Our
own pilot trees are private, so this page records the same metrics on every
public BT.CPP v3 tree in the test fixtures: the BehaviorTree.CPP 3.8.8
examples, the Groot 1 test data and the Nav2 (Humble) navigator trees.

These numbers are produced by `beehave stats` and pinned by the snapshot tests
in `tests/integration/test_public_trees.py`, so they cannot drift silently.

## Metrics

| Tree | Source | Nodes | Actions | Reduction | Transitions | Longest guard | Approximated (breakage) |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `BehaviorTree` (btcpp-subtree-test) | btcpp-v3 | 11 | 6 | 45% | 13 | 0 | none |
| `ParentIncludeChildIncludeParent` (btcpp-nested-includes) | btcpp-v3 | 7 | 0 | 100% | 1 | 0 | none |
| `MainTree` (groot-crossdoor) | groot | 13 | 5 | 62% | 13 | 1 | RetryUntilSuccessful ×1 |
| `BehaviorTree` (groot-show-all) | groot | 15 | 1 | 93% | 3 | 0 | ReactiveFallback ×1, ReactiveSequence ×1, Repeat ×1, RetryUntilSuccessful ×1 |
| `BehaviorTree` (groot-subtree-remapping) | groot | 7 | 2 | 71% | 5 | 0 | none |
| `BehaviorTree` (groot-key-reordering) | groot | 18 | 7 | 61% | 24 | 3 | none |
| `MainTree` (nav2-follow-point) | nav2 | 8 | 3 | 62% | 7 | 0 | GoalUpdater ×1, KeepRunningUntilFailure ×1, PipelineSequence ×1, RateController ×1 |
| `MainTree` (nav2-replanning-recovery) | nav2 | 18 | 9 | 50% | 20 | 1 | PipelineSequence ×1, RateController ×1, ReactiveFallback ×1, RecoveryNode ×3, RoundRobin ×1 |
| `MainTree` (nav2-goal-patience) | nav2 | 24 | 11 | 54% | 24 | 1 | PathLongerOnApproach ×1, PipelineSequence ×1, RateController ×1, ReactiveFallback ×1, ReactiveSequence ×1, RecoveryNode ×3, RetryUntilSuccessful ×1, RoundRobin ×1 |
| `MainTree` (nav2-replan-if-invalid) | nav2 | 23 | 9 | 61% | 22 | 2 | PipelineSequence ×1, RateController ×1, ReactiveFallback ×1, ReactiveSequence ×1, RecoveryNode ×3, RoundRobin ×1 |
| `MainTree` (nav2-odometry-calibration) | nav2 | 10 | 8 | 20% | 17 | 0 | Repeat ×1 |

Nav2 trees are analysed together with Nav2's own `nav2_tree_nodes.xml`, which
declares which of its nodes are conditions:

```console
$ beehave stats navigate_to_pose_w_replanning_and_recovery.xml nav2_tree_nodes.xml
```

## What we learned

- **Coverage: 11 of 11.** Every public v3 tree loads, flattens and walks with
  no manual edits. All four v4 trees are refused with a clear message,
  including BT.CPP's own `Check.xml`, which has no `BTCPP_format` marker and is
  recognised by its `SequenceWithMemory` node.
- **Reduction.** The graph shows 20% to 100% fewer boxes than the tree has
  nodes, 61% for the median tree. Trees made mostly of actions in a row, like
  `odometry_calibration`, shrink least, which is expected: there is little
  control logic to hide.
- **Guards stay short.** The longest raw guard is 3 terms, before any
  simplification. The plan's readability target is "about 3 terms after
  simplification".
- **Breakage is concentrated.** Two groups explain every approximated node:
  1. **Reactive nodes and loops** (`ReactiveSequence`, `ReactiveFallback`,
     `RetryUntilSuccessful`, `Repeat`, `KeepRunningUntilFailure`). These are
     the Phase 2 hard cases already planned.
  2. **Nav2's custom nodes** (`RecoveryNode`, `PipelineSequence`,
     `RoundRobin`, `RateController`, `GoalUpdater`, `PathLongerOnApproach`).
     Their semantics are known but not built in. This suggests a Phase 2
     feature: let the project config say that a custom node "behaves like" a
     built-in one (for example `PipelineSequence: ReactiveSequence`), with a
     shipped preset for Nav2.
- **Real-world quirks found.** BT.CPP's own example `subtree_test.xml` uses
  compact subtree references (`<CheckStatus/>`) that BT.CPP 3.8 rejects at
  runtime. Beehave reads them as subtrees and warns.

## Still open

- [ ] The readability gate: someone who did not write a tree answers "what
      happens if X fails?" from the graph alone.
- [ ] The private pilot: the same metrics on our own mission and landing
      trees.
