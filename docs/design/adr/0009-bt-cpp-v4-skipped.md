# 0009. Read BT.CPP v4 with a third continuation for SKIPPED

- **Status:** Accepted
- **Date:** 2026-10-17

## Context

BehaviorTree.CPP v4 adds a fourth status, `SKIPPED`, and scripts that decide
it: pre-conditions (`_skipIf`, `_while`, `_successIf`, `_failureIf`) on any
node, `Precondition`, `SkipUnlessUpdated`, `ScriptCondition` and `Script`.
A Sequence or a Fallback whose children are **all** skipped is skipped too,
so one bit of history ("has any child run yet?") changes where execution
goes. The full reference is [the v4 research](../../research/btcpp-v4-xml.md).

The walk of [ADR 0003](0003-continuation-passing-walk.md) passes two
continuations, success and failure. It cannot say where a skipped node goes.

## Decision

- The walk passes **three** continuations: success, failure and skipped. The
  root's skipped continuation is a `SKIPPED` terminal, drawn only when a path
  reaches it. In v3 and py_trees nothing skips, so nothing changes there.
- A Sequence or a Fallback keeps two tracks: "some child ran" and "every
  child so far was skipped". A child that may skip is compiled once per track;
  results are cached, so the shared parts are built once.
- Pre-conditions wrap a node in the order BT.CPP checks them. `_while` is
  re-checked every tick; the interrupt edges that follow are approximated
  and reported ([ADR 0004](0004-approximate-and-report.md)).
- Scripts are guards. The label is the script with its whitespace collapsed,
  the negation is written the way BT.CPP would (`!ready`, `!(battery < 20)`),
  and keys inside scripts are remapped through subtrees like ports.
- A blackboard write (`Script`, `SetBlackboard`) ends what earlier checks
  decide on that path, so a check after a write is never pruned as
  contradictory.
- New model members: `PARALLEL_ALL`, `TRY_CATCH`, `PRECONDITION`,
  `LOOP_QUEUE`, `SKIP_UNLESS_UPDATED`, `SCRIPT`, `SCRIPT_CONDITION`,
  `ENTRY_UPDATED` and `SUBTREE_V4`, and `Node.scripts` for pre- and
  post-conditions, which are not ports.
- Constructs that make BT.CPP throw (a skipped `IfThenElse` condition,
  `else="IDLE"`) are reported as errors and draw no edge.

## Consequences

- One walk serves v3, v4 and py_trees; the gate of
  [ADR 0008](0008-formats-track.md) holds: the v3 and v4 versions of a tree
  give the same graph, which a property test checks on random trees.
- A second property test runs random v4 trees with `_skipIf` anywhere through
  a reference interpreter that knows `SKIPPED`
  ([ADR 0007](0007-test-driven-with-a-reference-interpreter.md)).
- Post-conditions are kept in the model but not drawn yet. Loops over a
  skippable child are drawn for one case and reported. Scripts are not parsed
  into an AST, so `a > b` and `b < a` are two conditions.
