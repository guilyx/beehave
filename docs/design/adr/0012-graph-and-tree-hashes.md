# 0012. Hash the action graph and the inlined tree separately

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

A robot, a review and a log need to name the tree they mean (roadmap FD3).
A file hash does not do it: reformatting a file changes it, and it misses the
subtrees a file includes. Two questions are also different: "is this the same
tree?" and "does this tree behave the same?". A BT.CPP v3 tree and its v4
version, or a tree with an extra `Inverter` pair, answer them differently.

## Decision

- Two SHA-256 hashes, written `sha256:<hex>`, both computed from the tree and
  its config alone:
  - the **tree hash**, over the canonical XML of the selected tree with every
    subtree inlined: no whitespace or comments, attributes sorted, port values
    after remapping, the source format and the tree ID in a header;
  - the **graph hash**, over a canonical JSON of the action graph: actions
    (id, label, type, ports, notes, subtrees) and edges (source, target,
    outcome, and each guard term's key and polarity).
- Source locations, file names, diagnostics and node ids are not hashed, so
  moving a tree to another file or renaming a control node keeps the graph
  hash.
- Each canonical form carries a version number. Changing a form changes its
  version and is listed in the changelog.
- The JSON output carries both (`graph_hash`, `tree_hash`), and
  `beehave graph --print-hash` prints them.

## Consequences

- Equal graphs have equal graph hashes and unequal graphs unequal ones; a
  property test checks this on random trees.
- The graph hash depends on the walk rules and on `beehave.yaml`, so it is
  compared between results of the same Beehave version and config. The tree
  hash depends on the tree only.
- A tree hash says nothing about behaviour on its own: two trees with
  different XML can have the same graph.
