# Python API

```python
import beehave

result = beehave.analyze("landing.xml")

print(beehave.to_text(result.graph))
print(result.stats.to_text())

for action in result.graph.actions:
    for edge in result.graph.outgoing(action.id):
        print(action.label, edge.outcome, edge.target, [str(lit) for lit in edge.guard])
```

## The pipeline, step by step

`analyze` is a shortcut for the four steps. You can run them yourself:

```python
from beehave import Config, build_graph, flatten, parse_file, to_mermaid

document = parse_file(
    "mission.xml", "subtrees.xml", config=Config(conditions=frozenset({"BatteryOK"}))
)
tree = flatten(document, "Mission")  # inline subtrees
graph = build_graph(tree)  # the action graph
print(to_mermaid(graph))
```

Use `parse_string(xml)` to parse XML held in memory.

## Main types

| Type | What it is |
| --- | --- |
| `Document` | Every tree loaded from the files, plus load diagnostics. |
| `FlatTree` | One tree with every subtree inlined. |
| `ActionGraph` | Vertices (`START`, actions, `SUCCESS`, `FAILURE`), edges and diagnostics. |
| `Vertex` | A box: `id`, `kind`, `label`, `type`, `ports`, `notes`, `subtrees`, `location`. |
| `Edge` | `source`, `target`, `outcome` (`None` from `START`) and `guard`. |
| `Stats` | The pilot metrics; `to_text()` and `to_dict()`. |

## Errors

Everything Beehave raises on bad input derives from `beehave.BeehaveError`:

| Exception | When |
| --- | --- |
| `ParseError` | The XML is malformed or not a valid BT.CPP v3 document. |
| `UnsupportedFormatError` | The file is in another format, such as BT.CPP v4. |
| `FlattenError` | A subtree is missing or includes itself. |
| `TreeSelectionError` | No tree, or an unknown tree, was selected. |
| `ConfigError` | The config file is invalid. |

Each error has a `message` and, when known, a `location` (`file`, `line`).

## Stability

Beehave is in alpha (0.x). The names above are the public API; anything not
exported from `beehave` may change without notice.
