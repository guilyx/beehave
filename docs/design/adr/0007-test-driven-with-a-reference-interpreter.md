# 0007. Test-driven, with a reference interpreter

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Beehave's output is something people will trust instead of reading the XML.
A wrong arrow is worse than no graph. Example-based tests catch the cases we
think of; they miss the combinations we do not.

## Decision

- We work test-first: a failing test, then the code, then the refactor.
- Unit tests (`tests/unit/`) describe each step with small trees written
  inline, in the form `A -success-> B [guard]`.
- Snapshot tests (syrupy) pin the exact text, Mermaid, DOT and JSON output for
  reference trees. Changes show up as reviewable diffs.
- Property tests (`tests/property/`, Hypothesis) generate random trees and
  random outcomes, run them in a small reference interpreter, and check that
  following the graph gives the same actions and result, with exactly one
  matching edge at every step.
- Coverage must stay at or above 95%.

## Consequences

- A new walk rule is not done until the reference interpreter knows the node
  and the property test passes.
- The reference interpreter is the executable definition of "what the tree
  does". It must stay small and obviously correct.
