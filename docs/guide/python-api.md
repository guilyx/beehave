# Python API

```python
import beehave

result = beehave.analyze("examples/mobile/navigate_to_goal.xml")

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
    "mission.xml", "subtrees.xml", config=Config(conditions=frozenset({"IsBatteryOK"}))
)
tree = flatten(document, "MainTree")  # inline subtrees
graph = build_graph(tree)  # the action graph
print(to_mermaid(graph))
```

Use `parse_string(xml)` to parse XML held in memory. Both detect whether the
XML is BT.CPP v3 or v4; `document.format` says which (`"btcpp-v3"` or
`"btcpp-v4"`).

## py_trees trees

Pass the root of a py_trees tree, or its `BehaviourTree`, to
`analyze_py_trees`. The tree is only read: no behaviour is set up or ticked.

```python
import beehave
from my_robot.trees import create_root

config = beehave.Config(conditions=frozenset({"IsBatteryLow"}))
result = beehave.analyze_py_trees(create_root(), config=config)
print(beehave.to_mermaid(result.graph))
```

`from_py_trees(root)` gives the `Document` alone. `load_py_trees(spec,
**kwargs)` imports a factory by name and calls it, as `--py-trees` does on the
command line; **it runs that code**. py_trees itself is an optional
dependency: `pip install 'beehave-bt[py-trees]'`, or use the py_trees of your
ROS 2 distribution.

## Main types

| Type | What it is |
| --- | --- |
| `Document` | Every tree loaded from the files, plus load diagnostics. |
| `FlatTree` | One tree with every subtree inlined. |
| `ActionGraph` | Vertices (`START`, actions, `SUCCESS`, `FAILURE`, and `SKIPPED` for v4 trees that can skip), edges and diagnostics. |
| `Vertex` | A box: `id`, `kind`, `label`, `type`, `ports`, `notes`, `subtrees`, `location`. |
| `Edge` | `source`, `target`, `outcome` (`None` from `START`) and `guard`. |
| `Stats` | The Phase 1 metrics; `to_text()` and `to_dict()`. |

## Errors

Everything Beehave raises on bad input derives from `beehave.BeehaveError`:

| Exception | When |
| --- | --- |
| `ParseError` | The XML is malformed or not a valid BT.CPP document, the files mix versions, or a py_trees factory could not be imported or raised. |
| `UnsupportedFormatError` | The input is in a format Beehave does not read, such as py_trees XML, or py_trees is missing. |
| `FlattenError` | A subtree is missing or includes itself. |
| `TreeSelectionError` | No tree, or an unknown tree, was selected. |
| `ConfigError` | The config file is invalid. |

Each error has a `message` and, when known, a `location` (`file`, `line`).

## Stability

Beehave is in alpha (0.x). The names above are the public API; anything not
exported from `beehave` may change without notice.
