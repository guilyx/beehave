# 0014. Leave bookkeeping actions out of the graph, and keep their results as guards

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

Trees are full of actions that do not act on the world: logging, publishing a
status, copying a blackboard value. As boxes they sit between the actions that
matter, so "what runs after `TakeOff`?" answers "`LogMessage`" (roadmap FD7).
Only the project knows which of its actions are bookkeeping. Some of them can
fail, and a failure changes what runs next.

## Decision

- `beehave.yaml` gets `bookkeeping:`, a list of node types, or a mapping that
  says which never fail (`{never_fails: true}`). Only leaves qualify, they are
  declared like conditions and actions, and a built-in listed there is ignored
  with a warning. The model marks them with `Semantics.BOOKKEEPING`.
- The walk gives a bookkeeping node no vertex. Its entry is a branch on its
  own result, keyed by node, so the edges through it are joined up and carry
  the guard `<name> succeeded` or `<name> failed`. When it never fails, or both
  results lead to the same place, there is no branch.
- It counts as a blackboard write: checks made before it do not decide checks
  made after it, since Beehave cannot know what it writes.

## Consequences

- The graph keeps every path the tree can take: a property test runs random
  trees with bookkeeping actions through the reference interpreter and checks
  that the graph visits the real actions in the order they run, with one edge
  at each step.
- Collapsing never hides a failure path; the guard says which result leads
  where. Listing a bookkeeping action that in fact never fails as such keeps
  the graph smallest.
- A bookkeeping node keeps its runtime id and path, so a log that names it can
  still be matched; it just has no vertex.
