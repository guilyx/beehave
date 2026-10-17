# 0004. Approximate, and always report it

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Real trees contain nodes Phase 1 cannot model exactly: reactive sequences and
fallbacks (preemption), Retry and Repeat (loops), Parallel, and custom
controls and decorators with unknown semantics. Refusing such trees would make
the tool useless on real missions. Silently approximating them would make it
dangerous: a reader would trust a graph that is subtly wrong.

## Decision

Phase 1 walks these nodes with a simple, documented approximation (for
example, a reactive sequence is walked like a plain sequence), and **always**
emits a diagnostic with the node type, the approximation used and the source
location.

- The CLI prints diagnostics on stderr (`--quiet` hides them).
- The JSON output carries them.
- `beehave stats` counts them per node type: this is the plan's "breakage"
  metric, the list of what Phase 2 has to fix.

## Consequences

- Beehave runs on any tree from day one.
- The graph is honest about where it is approximate.
- Each Phase 2 rule removes a diagnostic. Progress is measurable.
