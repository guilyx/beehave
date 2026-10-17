# 0010. Read py_trees trees live, and import user code only on request

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

A py_trees tree has no file format that keeps what the walk needs. It is
built in Python, usually by a function such as `create_root()`; its dot
export drops decorator parameters and blackboard expressions, and the XML of
py_trees 2.5+ is experimental and only loads through py_trees itself. The
full reference is [the py_trees research](../../research/py-trees.md).

Getting the tree means importing the user's module and calling the function.
That runs code. Until now Beehave only ever read files that may come from
anywhere ([ADR 0005](0005-python-minimal-dependencies.md)).

## Decision

- **The adapter reads a live tree.** `beehave.from_py_trees(root)` turns a
  `Behaviour` or a `BehaviourTree` into the shared model
  ([ADR 0002](0002-one-model-many-parsers.md)). It only reads attributes: it
  never calls `setup()`, `tick()`, an `EternalGuard` condition or a callable
  comparison value.
- **Importing is a separate, explicit step.** `beehave.load_py_trees(spec)`
  and `beehave graph --py-trees module:function` import and call a factory.
  Nothing else does: not a file's contents, not `beehave.yaml`. Running
  `beehave` in an untrusted checkout never runs its code unless asked to.
- **Classes are matched by the class that owns their tick logic**, the
  nearest class in the MRO that defines `tick` or `update`. This tells
  `WaitFor…` apart from the `Check…` class it subclasses, and keeps the
  semantics of a user subclass that only changes `__init__`.
- `Sequence` and `Selector` map to the plain or reactive BT.CPP node by
  their `memory` flag; `EternalGuard` becomes a reactive sequence over its
  condition; blackboard checks become guards labelled by their expression.
- User behaviours are actions unless the config lists their class, or a base
  class, under `conditions`. A condition's name is part of its identity,
  because it is often all that tells two instances of one class apart.
- New model members: `PASS_THROUGH`, `STATUS_MAP`, `RUN_ONCE`,
  `ALWAYS_RUNNING`, `WAIT` and `BLACKBOARD_CONDITION`.
- py_trees is an optional extra, imported lazily, supported from 2.2.

## Consequences

- py_trees users get the same graph, renderers and stats as BT.CPP users. The
  py_trees versions of our examples give the same graph as the XML ones,
  except where py_trees has no equivalent node (no `IfThenElse`).
- `--py-trees` has the trust model of `pytest`: only point it at code you
  would run yourself, and treat it like running tests in CI on pull requests.
- py_trees XML is refused by the BT.CPP parsers with a pointer to
  `--py-trees`, because it looks like BT.CPP v3 but means something else.
