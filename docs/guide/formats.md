# Formats

Beehave reads three formats. Each one becomes the same internal model, so the
graph, the renderers and the stats work the same way for all of them.

| Format | How to read it | How Beehave knows |
| --- | --- | --- |
| BehaviorTree.CPP v3 | `beehave graph tree.xml` | `BTCPP_format="3"`, or no v4-only construct |
| BehaviorTree.CPP v4 | `beehave graph tree.xml` | `BTCPP_format="4"`, or a v4-only construct |
| py_trees 2.2 and newer | `beehave graph --py-trees module:function` | you say so |

The rule all formats follow: **the same tree gives the same graph**. Every
example in [`examples/`](examples.md) exists in all three formats, and the
tests check that their graphs match.

## BehaviorTree.CPP: v3 or v4?

A file says which version it is with `BTCPP_format` on its `<root>`. Many
files have no marker, so Beehave also looks for constructs that only exist in
v4:

- v4-only nodes, such as `Script`, `SequenceWithMemory`, `Sleep`, `TryCatch`;
- pre- and post-conditions, such as `_skipIf` or `_onSuccess`, and `_autoremap`;
- the port values `{=}` and `{@key}`;
- `success_count` or `failure_count` on `Parallel`.

A node type you declare in `<TreeNodesModel>` or in the
[config](configuration.md) is never taken as evidence, so a v3 project can
still have its own `Sleep` action. A file with neither a marker nor a v4
construct is read as v3; a models-only file takes the version of the others.
Files that mix v3 and v4 are refused, because BT.CPP cannot load them
together either.

## What v4 adds

### SKIPPED

A v4 node can be **skipped**: it returns neither success nor failure, and its
parent moves on. A `Sequence` or a `Fallback` whose children are all skipped
is skipped too. When a whole tree can be skipped, its graph gets a `SKIPPED`
terminal:

```xml
<Sequence>
  <Charge _skipIf="battery &gt; 80"/>
  <Patrol _skipIf="!ready"/>
</Sequence>
```

```text
START --[battery > 80 and !ready]--> SKIPPED
START --[battery > 80 and ready]--> Patrol
START --[!(battery > 80)]--> Charge
Charge --[success and !ready]--> SUCCESS
Charge --[success and ready]--> Patrol
Charge --[failure]--> FAILURE
Patrol --[success]--> SUCCESS
Patrol --[failure]--> FAILURE
```

### Scripts as guards

`ScriptCondition`, `Precondition` and the four pre-conditions are scripts.
Beehave shows them as guards, written the way BT.CPP writes them:
`battery < 20` holds, `!(battery < 20)` does not. Pre-conditions are checked
in BT.CPP's order: `_failureIf`, `_successIf`, `_skipIf`, then `_while`.

A `Script` or a `SetBlackboard` may change what a later check reads, so a
check after a write is never decided by the same check before it.

### Subtrees

v4 `<SubTree>` remapping is followed: `inner="{outer}"`, the same-name form
`inner="{=}"`, `{@key}` for the root blackboard, local literals, and
`_autoremap="true"`, which keeps private `_keys` local. Keys inside scripts
are remapped too, so a guard shows the key the subtree really reads.

### What is approximated

As in v3, nodes Beehave cannot model exactly in one pass are drawn with a
documented approximation and reported: reactive nodes, `Parallel` and
`ParallelAll`, loops (`Repeat`, `RetryUntilSuccessful`, `Loop*`), `Timeout`,
`RunOnce`, and `_while` while a node is running. Post-conditions
(`_onSuccess`, `_post`…) are read but not drawn yet. Constructs that make
BT.CPP throw, such as a skipped first child of `IfThenElse`, are reported as
errors and draw no edge. The [v4 reference](../research/btcpp-v4-xml.md) has
the rule for every node.

## py_trees

A py_trees tree is built in Python, so Beehave reads the tree a function
returns:

```console
$ beehave graph --py-trees my_robot.trees:create_root
$ beehave graph --py-trees trees/mission.py:create_root -c beehave.yaml
```

```python
import beehave
from my_robot.trees import create_root

print(beehave.to_text(beehave.analyze_py_trees(create_root()).graph))
```

!!! warning "This runs your code"
    `--py-trees` and `load_py_trees` import your module and call the function.
    Only point them at code you would run yourself. Nothing else makes Beehave
    import anything: not a tree file, not `beehave.yaml`. Converting a tree
    only reads it; no behaviour is set up or ticked.

### How py_trees nodes map

| py_trees | Walked like |
| --- | --- |
| `Sequence(memory=True)`, `Selector(memory=True)` | BT.CPP `Sequence`, `Fallback` |
| `Sequence(memory=False)`, `Selector(memory=False)` | `ReactiveSequence`, `ReactiveFallback` |
| `Parallel` | `Parallel`, with its policy recorded |
| `Inverter`, `FailureIsSuccess`, `SuccessIsFailure` | `Inverter`, `ForceSuccess`, `ForceFailure` |
| `Retry`, `Repeat`, `FailureIsRunning`, `SuccessIsRunning` | retry and repeat loops, noted on the action |
| `EternalGuard` | a reactive sequence over its condition and its child |
| `CheckBlackboardVariableValue` and the other checks | a guard such as `battery_level < 20` |
| `WaitFor…`, `timers.Timer` | an action that only succeeds |
| `Running`, `Dummy` | an action that never finishes |
| `Success`, `Failure`, `SetBlackboardVariable` | no box: they only route |
| your own behaviours | actions, or conditions if the config lists them |

"memory" in py_trees only means "resume at the child that was running", which
is what a plain BT.CPP `Sequence` does. A user class keeps the semantics of
the py_trees class it extends, as long as it does not override `tick` or
`update`.

### Conditions

py_trees has no condition type: a check is a behaviour like any other. List
your check classes, or a base class they share, in `beehave.yaml`:

```yaml
conditions:
  - Check          # every behaviour derived from Check
  - IsBatteryLow
```

### Limits

- The tree is read as the function returns it. Trees that change while they
  run (`insert_subtree`, dynamic loading) are not followed.
- Decisions passed through the blackboard (`StatusToBlackboard`, the
  `oneshot` idiom) are not tracked, so some guard combinations shown cannot
  happen.
- py_trees XML (2.5+) looks like BT.CPP v3 but means something else. Beehave
  refuses it with a pointer to `--py-trees`: load it with py_trees, then read
  the tree.

The [py_trees reference](../research/py-trees.md) has the tick semantics of
every class and how each one is read.
