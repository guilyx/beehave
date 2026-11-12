# 0015. Diff action graphs by stable path, and pair moved actions

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

A reviewer wants to know what a change to a tree does to its behaviour: which
actions and transitions it adds or removes, which guards it changes, which
ends it makes reachable (roadmap QM4). Display ids (`a1`, `a2`…) and runtime
ids number nodes in document order, so one inserted action renumbers
everything after it. A diff keyed by numbers would report the whole tree as
changed.

## Decision

- `beehave.diff_graphs(old, new)` matches actions by their stable path
  ([ADR 0011](0011-node-paths-and-runtime-ids.md)), terminals by kind, and
  guard terms by condition key. Checks that belong to one node are keyed by
  that node's path, not by child indices, so they match too.
- An action whose path is gone and one whose path is new, with the same label,
  type, ports, notes and subtrees, are one action moved, when no other action
  could pair with either. A move is listed but is not a change of the graph.
- A step (source, outcome, target) kept by both graphs with different guards
  is one guard change, not a transition removed and one added.
- Reachability is computed from `START` over the edges, guards left out, for
  vertices present in both graphs.
- The transition score takes the old graph as reference and counts steps
  without guards: precision, recall and F1, each 1 when there is nothing to
  compare.
- Output as text, Markdown (for pull-request comments) and JSON (schema
  `beehave.graph-diff`, version 1); `--exit-code` exits with 3 on a change.

## Consequences

- Inserting or deleting a node changes only what it touches in the diff.
- Renaming a node is a removal and an addition. Identical actions moved
  together cannot be told apart and show the same way.
- Reachability ignores guard satisfiability, so an edge whose guard can never
  hold still counts as a way through.
