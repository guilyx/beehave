# Changelog

All notable changes to Beehave are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(with [PEP 440](https://peps.python.org/pep-0440/) version strings). While the
version is 0.x, a minor release may include breaking changes; they are always
listed here under **Changed** or **Removed**.

## [Unreleased]

The first release: Phase 1 of the roadmap, the action graph.

### Added

- BehaviorTree.CPP v3 XML parser. It follows `<include>` tags, reads
  `<TreeNodesModel>` to classify custom nodes, checks the structure BT.CPP
  itself checks (number of children, required IDs), keeps source locations
  for messages, and refuses DTDs. BT.CPP v4 files are detected, by their
  `BTCPP_format` marker or by v4-only nodes, attributes and port values, and
  rejected with a clear error.
- Loading follows BT.CPP 3.8: includes load before the including file's
  trees, the first definition of a duplicate tree ID wins (with a warning),
  and compact subtree references are accepted with a warning.
- Subtree flattening: `SubTree` and `SubTreePlus` are inlined with their port
  remapping, including `__autoremap`, `__shared_blackboard` and `${key}`.
  Remapping mistakes BT.CPP accepts silently are reported.
- Continuation-passing walk from a flattened tree to an action graph: actions
  become vertices with success and failure edges, and conditions become
  guards on those edges instead of boxes. Nodes Phase 1 can only approximate
  (reactive nodes, `Parallel`, loops, unknown custom nodes) are walked with a
  documented approximation and always reported as diagnostics.
- Renderers for plain text, Mermaid, Graphviz DOT and JSON.
- The `beehave` command line: `beehave graph` (the action graph in any
  format), `beehave stats` (size, reduction, longest guard and approximated
  nodes, also as JSON) and `beehave trees` (list the trees in the files).
- An optional per-project `beehave.yaml` to declare which custom nodes are
  conditions or actions.
- A typed Python API: `beehave.analyze()` and each pipeline step on its own.
- Property-based tests (Hypothesis) that check the action graph against a
  reference interpreter on random trees and outcomes, plus snapshot tests of
  every output format.
- Integration tests on public BT.CPP, Groot and Nav2 trees, with the Phase 1
  metrics recorded in the docs.

[Unreleased]: https://github.com/guilyx/beehave/commits/main/
