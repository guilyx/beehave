# Node ids and paths

A log, a test, a diff or an editor needs to point at one node of a tree.
Beehave gives every node three identifiers, computed from the tree alone, and
records them on every action and on every condition in a guard. Nothing is
read from a running robot.

| Identifier | Example | What it is for |
| --- | --- | --- |
| Path | `mission_with_failsafe/mission/Arm` | Beehave's stable key. Diffs and plans use it. |
| Runtime id | `6` (or `5` from 0) | The node's position in the instantiated tree, as runtimes number it. |
| Runtime path | `ReturnToLaunch::14/Land::21` | BehaviorTree.CPP v4's `TreeNode::fullPath()`. |

The *instantiated tree* is the tree with every subtree inlined, as the runtime
builds it: a tree used twice has two copies.

## Paths

A path names each node from the root down, separated by `/`:

- a node with a `name` is named by it;
- a node without one is named by its type (`Sequence`, `Arm`);
- a subtree node without one is named by the ID of the tree it includes;
- siblings that would get the same name are numbered `#2`, `#3`… in document
  order: `Sequence/Act`, `Sequence/Act#2`.

`/`, `#` and `%` inside a name are written `%2F`, `%23` and `%25`.

A path does not change when other nodes are added, removed or moved
elsewhere in the tree, so it keeps naming the same node across edits. Give
nodes a `name` to make their paths fully stable: two unnamed siblings of one
type are told apart only by their order.

In py_trees every behaviour has a name, so the path is the names from the root
down.

## Runtime ids

Runtime ids number every node of the instantiated tree depth first, in
pre-order: a node comes before its children, and a `SubTree` node comes right
before the nodes of the tree it includes. Every node counts: controls,
decorators, conditions, actions and subtree nodes. Two schemes share that
order:

| Scheme | First id | Matches |
| --- | --- | --- |
| `btcpp-v4` (default) | 1 | `TreeNode::UID()` in BehaviorTree.CPP v4 |
| `preorder` | 0 | Runtimes that publish their own indices that way, from 0 |

The `btcpp-v4` ids and runtime paths reproduce BehaviorTree.CPP's own
[observer example](https://github.com/BehaviorTree/btcpp_website/blob/9cc7aadf176194aa19150d224f62368c9c7f81b0/docs/tutorial-basics/tutorial_10_observer.md),
which is one of Beehave's tests.

BehaviorTree.CPP v3 numbers nodes per process, not per tree, so for a v3 tree
these are the ids v4 would give the same tree. For py_trees, which has no
numeric ids, they count Beehave's view of the tree, where an `EternalGuard` is
a reactive sequence over its condition and its child, and there is no runtime
path.

## List them

`beehave ids` lists every node of a tree:

```console
$ beehave ids examples/aerial/drone_mission.xml -q
ID  KIND       VERTEX  RUNTIME PATH                             PATH
1   control    -       mission_with_failsafe                    mission_with_failsafe
2   control    -       failsafe                                 mission_with_failsafe/failsafe
3   condition  -       IsBatteryCritical::3                     mission_with_failsafe/failsafe/IsBatteryCritical
4   action     a1      LandNow::4                               mission_with_failsafe/failsafe/LandNow
5   control    -       mission                                  mission_with_failsafe/mission
6   action     a2      Arm::6                                   mission_with_failsafe/mission/Arm
...
14  subtree    -       ReturnToLaunch::14                       mission_with_failsafe/mission/ReturnToLaunch
15  control    -       ReturnToLaunch::14/Sequence::15          mission_with_failsafe/mission/ReturnToLaunch/Sequence
...
```

`VERTEX` is the action's id in the graph. `--scheme preorder` numbers from 0,
and `--json` prints the same table as a document (schema
`beehave.runtime-ids`) with each node's parent, type, name and location.

## From Python

```python
import beehave

result = beehave.analyze("examples/aerial/drone_mission.xml")

# Every node, by runtime id, controls and conditions included.
nodes = beehave.runtime_ids(result.tree, beehave.IdScheme.PREORDER)
print(nodes[13].ref.path, nodes[13].kind)  # the ReturnToLaunch subtree node

# From an id in a log to the action it ran.
vertex = result.graph.vertex_for(6)  # btcpp-v4 scheme by default
print(vertex.label, vertex.node.path)  # Arm mission_with_failsafe/mission/Arm

# The node behind each check of a guard.
for edge in result.graph.outgoing("start"):
    for literal in edge.guard:
        print(literal, literal.condition.node.uid)
```

`Vertex.node` and `Condition.node` are `NodeRef`s: `path`, `uid`, `index`
(from 0) and `runtime_path`, and `runtime_id(scheme)`. When a guard checks the
same condition at two nodes, it keeps the first. In the JSON output each action
and each guard term carries the same fields under `tree_node`
([Output formats](output-formats.md)).
