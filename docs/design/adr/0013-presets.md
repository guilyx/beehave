# 0013. Let the config give a custom node a preset

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

Custom controls and decorators are the largest source of approximations on
real trees: Beehave walks an unknown control like a `Sequence` and an unknown
decorator as transparent, and reports both
([ADR 0004](0004-approximate-and-report.md)). Many of them behave exactly like
a node Beehave knows (Nav2's `PipelineSequence`, a project's own `Fallback`
with logging), or follow a handful of generic patterns: run the child until
it succeeds, poll a check until it holds, loop until a blackboard flag is set,
run children in parallel until one succeeds (roadmap F4a).

A project's own node may also share a name with a node of another BT.CPP
version (a v3 project with its own `ParallelAll`), which today makes the file
read as v4.

## Decision

- `beehave.yaml` gets a `nodes:` mapping from node type to a preset:
  `Name: preset`, or `Name: {behaves_like: preset, <options>}`. Presets live
  in `beehave.presets`; each fixes the node's kind, how many children it may
  have, and its walk rule. Options are checked against the preset.
- The model records it: `Node.behaves_like` and `Node.options`, and new
  `Semantics` members for behaviours no built-in has: `PIPELINE_SEQUENCE`,
  `ROUND_ROBIN`, `PARALLEL_FIRST_SUCCESS`, `UNTIL_SUCCESS` and
  `LOOP_UNTIL_FLAG`. Diagnostics name the preset: `KeepTrying (until_success): …`.
- A node type under `nodes` is declared, like one under `conditions` or
  `actions`: never evidence of BT.CPP v4 or of py_trees XML. A preset for a
  built-in of the file's version is ignored with a `preset-ignored` warning.
- Loops are walked up to the point where the child starts again, and no
  further: an `until_success` child that fails has no failure edge, and a
  `loop_until_flag` child that succeeds leads to the exit only when the flag
  is set. The edge back to the child needs cycles (FD5); when the child can
  run an action, that missing edge is reported. A loop whose child only
  checks something is exact.
- Concurrent presets (`parallel_first_success`) keep the existing parallel
  approximation, as one-after-another children, and are reported.

## Consequences

- Exact presets are checked against the reference interpreter on random
  trees, loops included: with every condition and action keeping its value,
  a loop ends in its first pass or never, and the graph has no edge exactly
  where the interpreter would spin.
- The graph never shows an edge a loop cannot take, at the cost of missing
  the edges back to the child until FD5.
- Nav2's per-distro presets and its bounded loops (`RecoveryNode`) are left
  for later; they need counted loops.
