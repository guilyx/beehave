# 0002. One internal model, many parsers

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

We start with BehaviorTree.CPP v3 because the first trees we care about use
`SubTreePlus`. v4 comes next, and other libraries (py_trees, Nav2 trees which
are BT.CPP underneath) later. The formats name the same ideas differently:
`SequenceStar` in v3 is `SequenceWithMemory` in v4, `SubTreePlus` in v3 is
`SubTree` in v4.

## Decision

Every parser produces the same format-agnostic model (`beehave.model`). A node
carries a **kind** (control, decorator, condition, action, subtree) and a
**semantics** (what it does, e.g. `SEQUENCE_WITH_MEMORY`), plus its original
type name, ports, children and source location.

Flatten, walk and render only ever see this model.

## Consequences

- Adding a format means adding a parser. Nothing downstream changes.
- Format-specific details must be translated into the model, or kept as
  ports. If a format has a concept the model cannot express, we extend the
  model with a new ADR.
- The model is also where the Phase 3 ontology (action, condition, zone,
  mission phase) will attach.
