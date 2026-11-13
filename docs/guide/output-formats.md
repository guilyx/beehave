# Output formats

All formats are deterministic: the same tree always gives the same output.

## Text

One transition per line:

```text
SOURCE --[outcome and guard]--> TARGET
```

- Edges leaving `START` have no outcome: `START --[IsBatteryCritical]--> LandNow`.
- Actions that share a label get a suffix: `FlyToZone#1`, `FlyToZone#2`.
- Notes such as `retry ×3` are listed at the end.

## Mermaid

A `flowchart TD`. Actions are boxes, `START` is a circle, `SUCCESS` and
`FAILURE` are rounded terminals. Success edges are solid, failure edges dashed.
Edge labels hold the outcome and the guard.

A BehaviorTree.CPP v4 tree that can be skipped as a whole (every path through
it can hit a `_skipIf`, say) also has a `SKIPPED` terminal, with a dashed
outline. It only appears when some path reaches it.

## Graphviz DOT

A `digraph` named after the tree, with the same conventions as Mermaid. Render
it with `dot -Tsvg` or `dot -Tpng`.

## JSON

A versioned document meant for other tools, including a future operator view.

```json
{
  "schema": "beehave.action-graph",
  "version": 1,
  "tree": "DroneMission",
  "source_format": "btcpp-v3",
  "graph_hash": "sha256:e3527ef932c22b8e4269b525f0b715993d09c8041ec7599ac4ec96936b9d192e",
  "tree_hash": "sha256:a2a6aac5293fb84efadc5217879b2995bf29c8a1b2b9e33b0694a319d197d6dd",
  "nodes": [
    {"id": "start", "kind": "start", "label": "START"},
    {
      "id": "a4",
      "kind": "action",
      "label": "FlyToWaypoint",
      "type": "FlyToWaypoint",
      "ports": {"waypoint": "{survey_point}"},
      "notes": ["retry ×3"],
      "subtrees": [],
      "location": {"file": "examples/aerial/drone_mission.xml", "line": 23},
      "tree_node": {
        "path": "mission_with_failsafe/mission/ForceSuccess/survey/RetryUntilSuccessful/FlyToWaypoint",
        "uid": 12,
        "index": 11,
        "runtime_path": "FlyToWaypoint::12"
      }
    },
    {"id": "success", "kind": "success", "label": "SUCCESS"},
    {"id": "failure", "kind": "failure", "label": "FAILURE"}
  ],
  "edges": [
    {
      "from": "a3",
      "to": "a4",
      "outcome": "success",
      "guard": [
        {
          "condition": "IsBatteryOK",
          "key": "IsBatteryOK()",
          "holds": true,
          "tree_node": {
            "path": "mission_with_failsafe/mission/ForceSuccess/survey/IsBatteryOK",
            "uid": 10,
            "index": 9,
            "runtime_path": "IsBatteryOK::10"
          }
        }
      ]
    }
  ],
  "diagnostics": [
    {
      "code": "approximated",
      "severity": "warning",
      "message": "ReactiveFallback \"mission_with_failsafe\": walked like a Fallback; …",
      "node_type": "ReactiveFallback",
      "location": {"file": "examples/aerial/drone_mission.xml", "line": 11}
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `graph_hash`, `tree_hash` | Content hashes of the graph and of the inlined tree ([Hashes](#hashes)). |
| `nodes[].id` | `start`, `success`, `failure`, or `a1`, `a2`… for actions in document order. |
| `nodes[].kind` | `start`, `action`, `success` or `failure`. |
| `nodes[].ports` | Port values after subtree remapping. `{key}` is a blackboard entry. |
| `nodes[].subtrees` | The subtrees the action was inlined from, outermost first. |
| `edges[].outcome` | `success`, `failure`, or `null` for edges leaving `start`. |
| `edges[].guard` | A conjunction. Each term names a condition and whether it must hold. |
| `edges[].guard[].key` | The condition's identity: its type and port values, or the script. A check that belongs to one node (`WasEntryUpdated`, a bookkeeping action's result) is keyed by its type and [stable path](node-ids.md#paths), `Type@path`. |
| `nodes[].tree_node`, `edges[].guard[].tree_node` | The node the action or the check comes from: its stable `path`, its BT.CPP v4 `uid` (from 1), its `index` (from 0) and its BT.CPP v4 `runtime_path` (`null` for py_trees). See [Node ids and paths](node-ids.md). |
| `diagnostics` | What could not be modelled exactly, and where. |

The `version` field changes only when a change would break a consumer.
Adding fields does not bump it.

## Hashes

Two content hashes name what a result is about, so a robot, a review and a
log can say which tree they mean. Both are computed from the tree and the
config alone.

| Hash | Over | Changes when |
| --- | --- | --- |
| Tree hash | The selected tree with every subtree inlined, as canonical XML: no whitespace or comments, attributes sorted, port values after remapping. | A node, a port, a name or the nesting changes. Not when the file is reformatted, its attributes reordered, or the tree moved to another file. |
| Graph hash | The action graph: actions with their ports and notes, edges with their outcome and guard. | The graph changes. Not when only the XML does: the v3 and v4 versions of a tree, or a renamed `Sequence`, share it. |

```console
$ beehave graph examples/aerial/drone_mission.xml --print-hash -q
graph sha256:e3527ef932c22b8e4269b525f0b715993d09c8041ec7599ac4ec96936b9d192e
tree  sha256:a2a6aac5293fb84efadc5217879b2995bf29c8a1b2b9e33b0694a319d197d6dd
$ beehave graph examples/aerial/drone_mission_v4.xml --print-hash -q
graph sha256:e3527ef932c22b8e4269b525f0b715993d09c8041ec7599ac4ec96936b9d192e
tree  sha256:5756624c76d745dc717e65369f1ea1aa40b1116e8de46354bddf93b6a9e241cd
```

The graph depends on Beehave's walk rules and on `beehave.yaml` (which nodes
are conditions), so compare graph hashes made with the same Beehave version
and config. In Python: `beehave.graph_hash(graph)`, `beehave.tree_hash(tree)`
and `beehave.canonical_xml(tree)`, the text the tree hash is computed over
([ADR 0012](../design/adr/0012-graph-and-tree-hashes.md)).
