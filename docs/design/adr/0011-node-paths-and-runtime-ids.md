# 0011. Name nodes by a stable path, and compute runtime ids from the tree

- **Status:** Accepted
- **Date:** 2026-11-12

## Context

Logs, tests, diffs and editors need to point at one node of a tree, and then
at the vertex or the guard that node became (roadmap FD1 and FD2). Three kinds
of name are in use:

- BehaviorTree.CPP v4 numbers the nodes of an instantiated tree depth first
  from 1, a `SubTree` node before its contents (`TreeNode::UID()`), and builds
  a path from instance names, adding `::<uid>` to unnamed nodes
  (`TreeNode::fullPath()`, `xml_parsing.cpp`). Its loggers record both.
- Some runtimes publish their own indices: the same pre-order walk, from 0.
- Display ids (`a1`, `a2`…) number actions in document order. They change
  whenever an action is added before another one, and conditions have none.

UIDs and runtime paths shift when a node is inserted anywhere before them, so
they cannot key a diff. Beehave also stays static: it must compute every id
from the tree alone, never from a run.

## Decision

- Every node of the instantiated tree gets a `NodeRef`: a **path**, Beehave's
  stable key, and its **runtime ids**. Action vertices and guard conditions
  carry the `NodeRef` of the node they come from. `NodeRef`s take no part in
  graph equality, so two trees with the same behaviour still compare equal.
- A path segment is the node's `name`, else its type (for a subtree node, the
  ID of the tree it includes). Siblings with the same segment are numbered
  `#2`, `#3`… in document order. `/`, `#` and `%` are percent-escaped. The
  path starts at the root node, not at the tree ID, so renaming the tree
  keeps the keys.
- Runtime ids come in two schemes over the same pre-order walk, chosen with
  `IdScheme`: `btcpp-v4` from 1 and `preorder` from 0. Every node that the
  runtime creates counts, controls and decorators included, so
  `runtime_ids()` lists them all, not only actions.
- The runtime path is computed the way BT.CPP v4 does, for BT.CPP trees. It is
  checked against BT.CPP's own observer tutorial.
- A guard that checks one condition twice keeps the first node, as it keeps
  the first literal.

## Consequences

- A tool holding an id or a runtime path from a log finds the node, then the
  action or the guards it became, without running anything.
- Diffs and plans key nodes by path. Renaming a node, or reordering unnamed
  siblings of one type, changes its path; naming nodes avoids that.
- For BT.CPP v3, which numbers nodes per process, the ids are what v4 would
  give the same tree. For py_trees, ids count Beehave's model, where an
  `EternalGuard` becomes two nodes, and there is no runtime path.
- The JSON output gains a `tree_node` object on actions and guard terms. Adding
  fields does not change its version.
