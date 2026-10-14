# Output formats

All formats are deterministic: the same tree always gives the same output.

## Text

One transition per line:

```text
SOURCE --[outcome and guard]--> TARGET
```

- Edges leaving `START` have no outcome: `START --[Emergency]--> EmergencyLand`.
- Actions that share a label get a suffix: `FlyToZone#1`, `FlyToZone#2`.
- Notes such as `retry ×3` are listed at the end.

## Mermaid

A `flowchart TD`. Actions are boxes, `START` is a circle, `SUCCESS` and
`FAILURE` are rounded terminals. Success edges are solid, failure edges dashed.
Edge labels hold the outcome and the guard.

## Graphviz DOT

A `digraph` named after the tree, with the same conventions as Mermaid. Render
it with `dot -Tsvg` or `dot -Tpng`.

## JSON

A versioned document meant for other tools, including a future operator view.

```json
{
  "schema": "beehave.action-graph",
  "version": 1,
  "tree": "Mission",
  "source_format": "btcpp-v3",
  "nodes": [
    {"id": "start", "kind": "start", "label": "START"},
    {
      "id": "a3",
      "kind": "action",
      "label": "GoToZone",
      "type": "GoToZone",
      "ports": {"zone": "{mission_zone}"},
      "notes": ["retry ×3"],
      "subtrees": [],
      "location": {"file": "landing.xml", "line": 19}
    },
    {"id": "success", "kind": "success", "label": "SUCCESS"},
    {"id": "failure", "kind": "failure", "label": "FAILURE"}
  ],
  "edges": [
    {
      "from": "a2",
      "to": "a3",
      "outcome": "success",
      "guard": [{"condition": "BatteryOK", "key": "BatteryOK()", "holds": true}]
    }
  ],
  "diagnostics": [
    {
      "code": "approximated",
      "severity": "warning",
      "message": "ReactiveFallback: walked like a Fallback; …",
      "node_type": "ReactiveFallback",
      "location": {"file": "landing.xml", "line": 8}
    }
  ]
}
```

| Field | Meaning |
| --- | --- |
| `nodes[].id` | `start`, `success`, `failure`, or `a1`, `a2`… for actions in document order. |
| `nodes[].kind` | `start`, `action`, `success` or `failure`. |
| `nodes[].ports` | Port values after subtree remapping. `{key}` is a blackboard entry. |
| `nodes[].subtrees` | The subtrees the action was inlined from, outermost first. |
| `edges[].outcome` | `success`, `failure`, or `null` for edges leaving `start`. |
| `edges[].guard` | A conjunction. Each term names a condition and whether it must hold. |
| `edges[].guard[].key` | The condition's identity: its type and port values. |
| `diagnostics` | What could not be modelled exactly, and where. |

The `version` field changes only when a change would break a consumer.
Adding fields does not bump it.
