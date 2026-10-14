# 0001. Record architecture decisions

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Beehave is meant to grow into an open-source framework with outside
contributors. People joining later need to know why the code looks the way it
does, not only what it does.

## Decision

We record every significant design decision as an ADR in `docs/design/adr/`,
using [the template](template.md). "Significant" means: it changes the
pipeline, the internal model, the output formats, the dependencies, or the
public API.

## Consequences

- New contributors can read the reasoning instead of guessing it.
- Design changes go through a pull request that adds or supersedes an ADR,
  which gives a natural place for discussion.
- ADRs cost a little time. We keep them to one page.
