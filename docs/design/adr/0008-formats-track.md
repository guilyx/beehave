# 0008. Grow formats on their own track

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

The original plan put new formats inside the phases: BT.CPP v4 in Phase 2,
py_trees "later". Phase 1 is done, and the first users ask for the formats
they actually run: BT.CPP v4 (Nav2 Jazzy and newer, BT.CPP 4.x) and py_trees
(ROS 2 Python projects, and the input format of BehaVerify). Waiting for
Phase 2's guard work before reading their trees would leave them out for a
long time, for no technical reason: the model is shared
([ADR 0002](0002-one-model-many-parsers.md)).

## Decision

Formats become a separate track, worked alongside the phases:

- **F1** BT.CPP v3 (done), **F2** BT.CPP v4, **F3** py_trees, **F4** node
  presets (custom nodes that "behave like" a built-in one, Nav2 first).
- Every format produces the shared model. A phase feature (guards, gap
  report, operator view) lands once and applies to every format.
- Every format passes one gate: **the same tree gives the same graph**. We
  test it with the same tree written in each format (our examples, the Nav2
  Humble/Jazzy pairs) and with randomly generated trees.

## Consequences

- v4 and py_trees users are served before Phase 2, without forking the walk.
- A format cannot add semantics the model lacks without a new ADR; the
  cross-format equivalence tests keep parsers honest.
- The phase numbering from the original plan does not change.
