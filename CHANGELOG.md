# Changelog

All notable changes to Beehave are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html)
(with [PEP 440](https://peps.python.org/pep-0440/) version strings). While the
version is 0.x, a minor release may include breaking changes; they are always
listed here under **Changed** or **Removed**.

## [Unreleased]

The first release: Phase 1 of the roadmap, the action graph, for
BehaviorTree.CPP v3 and v4 and for py_trees.

### Added

- BehaviorTree.CPP v3 XML parser. It follows `<include>` tags, reads
  `<TreeNodesModel>` to classify custom nodes, checks the structure BT.CPP
  itself checks (number of children, required IDs), keeps source locations
  for messages, and refuses DTDs.
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
- BehaviorTree.CPP v4 XML parser, with every node BT.CPP 4.10 registers.
  `parse_file`, `parse_string`, `analyze` and the CLI detect the version, by
  the `BTCPP_format` marker or by v4-only nodes, attributes and port values,
  and refuse files that mix versions. Pre- and post-conditions are kept as
  scripts, the last definition of a duplicate tree wins, and v3-only nodes are
  refused with a pointer to their v4 form.
- v4 subtree remapping: `{=}`, `{@key}`, local literals, and `_autoremap`,
  which keeps private keys local. Keys inside scripts are remapped too.
- The `SKIPPED` status: the walk passes a third continuation, so a Sequence
  or a Fallback whose children are all skipped is skipped, and pre-conditions
  (`_failureIf`, `_successIf`, `_skipIf`, `_while`) wrap a node in BT.CPP's
  order. Script guards read as BT.CPP writes them (`battery < 20`,
  `!(battery < 20)`), and a blackboard write ends what earlier checks decide.
  A `SKIPPED` terminal is drawn when a tree can be skipped.
- Walk rules for `TryCatch`, `Precondition`, `SkipUnlessUpdated`,
  `WasEntryUpdated`, `Loop*`, `ParallelAll`, `RunOnce`, `Script`,
  `ScriptCondition` and `Sleep`. Constructs that make BT.CPP throw are
  reported as errors.
- A py_trees adapter: `beehave.from_py_trees()` and
  `beehave.analyze_py_trees()` read a live tree without running it, and
  `beehave graph --py-trees module:function` (with `--kwargs`) imports a
  factory and calls it. py_trees 2.2 and newer, as the optional extra
  `beehave-bt[py-trees]`. Composites, decorators and blackboard checks are
  mapped; user behaviours are actions unless the config lists their class or a
  base class under `conditions`.
- py_trees XML is refused with a pointer to `--py-trees`.
- Every example exists in BT.CPP v3, BT.CPP v4 and py_trees, and the tests
  check that all versions give the same graph.
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
  metrics recorded in the docs; on 39 public v4 trees, with v3/v4 pairs that
  must give the same graph; and on the py_trees demos.

[Unreleased]: https://github.com/guilyx/beehave/commits/main/
