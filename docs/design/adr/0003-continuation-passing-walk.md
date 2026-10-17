# 0003. A continuation-passing walk

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The core question is: for each action, what runs next on success and on
failure, and under which conditions? A naive walk that simulates execution
for every combination of condition values grows exponentially with the number
of conditions, and it struggles with nodes that send both outcomes to the same
place.

## Decision

We compile the tree in continuation-passing style. Each node is compiled with
two continuations ("where to go on success", "where to go on failure") and
returns its entry ("what runs first"). Actions become graph vertices whose
outgoing edges are their continuations. Conditions become branch points. In a
last step, branch points are expanded into guards on the edges, dropping
contradictory paths.

The full rule table is in the [Phase 1 specification](../phase-1.md#the-walk).

## Consequences

- Each node is visited once. The cost is linear in the tree size, plus the
  guard expansion, which is capped and reported when it hits the cap.
- Every control and decorator is a small, local rule. Adding a node type means
  adding one rule.
- Loops (Retry, Repeat) and preemption (reactive nodes) need continuations
  that point back to an earlier entry. The model supports that; Phase 2 will
  add those rules.
- Correctness is checked by property tests against a reference interpreter
  ([ADR 0007](0007-test-driven-with-a-reference-interpreter.md)).
