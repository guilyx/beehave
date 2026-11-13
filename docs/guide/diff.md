# Comparing two trees

`beehave diff` compares the action graphs of two versions of a tree: which
actions and transitions a change adds, removes or alters. It reads the two
trees and nothing else.

```xml
<!-- old.xml -->
<Sequence>
  <IsReady/>
  <Arm/>
  <TakeOff altitude="10"/>
  <Fallback name="work">
    <Survey/>
    <ReturnHome/>
  </Fallback>
</Sequence>

<!-- new.xml -->
<Sequence>
  <IsReady/>
  <Sequence name="prepare">
    <Arm/>
    <CheckMotors/>
  </Sequence>
  <TakeOff altitude="15"/>
  <Fallback name="work">
    <Survey/>
    <Land/>
  </Fallback>
</Sequence>
```

```console
$ beehave diff old.xml new.xml        # with IsReady listed under conditions
> action Sequence/Arm moved to Sequence/prepare/Arm
+ action Sequence/prepare/CheckMotors
+ action Sequence/work/Land
- action Sequence/work/ReturnHome
~ action Sequence/TakeOff: ports {altitude=10} -> {altitude=15}
+ Sequence/prepare/Arm --[success]--> Sequence/prepare/CheckMotors
+ Sequence/prepare/CheckMotors --[success]--> Sequence/TakeOff
+ Sequence/prepare/CheckMotors --[failure]--> FAILURE
+ Sequence/work/Land --[success]--> SUCCESS
+ Sequence/work/Land --[failure]--> FAILURE
+ Sequence/work/Survey --[failure]--> Sequence/work/Land
- Sequence/prepare/Arm --[success]--> Sequence/TakeOff
- Sequence/work/ReturnHome --[success]--> SUCCESS
- Sequence/work/ReturnHome --[failure]--> FAILURE
- Sequence/work/Survey --[failure]--> Sequence/work/ReturnHome
transitions: 6 of 10 kept, 12 now; precision 0.50, recall 0.60, F1 0.55
```

| Line | Meaning |
| --- | --- |
| `+ action`, `- action` | An action only the new, or only the old, graph has. |
| `~ action` | An action in both whose label, type, ports, notes or subtrees changed. |
| `> action … moved to …` | An action whose path changed and nothing else. A move alone is not a change. |
| `+ A --[…]--> B`, `- …` | A transition only one graph has. |
| `~ A --> B: guard - […]`, `guard + […]` | A step in both graphs whose guards changed. |
| `! X became reachable`, `became unreachable` | An action or an end that one graph reaches from `START` and the other does not. |
| `transitions:` | The transition score, below. |

## How actions are matched

Actions are matched by their [stable path](node-ids.md#paths), never by the
display ids `a1`, `a2`… or the runtime ids, which shift whenever a node is
added above them. Renaming a node or moving it changes its path. When one
action is gone and one is new with exactly the same content (label, type,
ports, notes and subtrees), the diff reports a move and names the action by
its new path everywhere else; when several could pair up, it reports them as
removed and added. Guard terms are matched by their condition key.

## The transition score

The old graph is the reference. A transition here is a step, source, outcome
and target, without its guard:

- **precision**: the share of the new graph's transitions the old graph has;
- **recall**: the share of the old graph's transitions the new graph keeps;
- **F1**: their harmonic mean.

Two identical graphs score 1, and so do two empty ones.

## Formats and CI

`-f markdown` writes a summary table and the changes as lists, for a
pull-request comment. `-f json` writes a document (schema
`beehave.graph-diff`, version 1) with the same content and both graph hashes.
`--exit-code` exits with 3 when the graphs differ, so a CI job can flag a
behaviour change:

```console
$ git show main:trees/mission.xml > /tmp/base.xml
$ beehave diff /tmp/base.xml trees/mission.xml -f markdown -o graph-diff.md --exit-code
```

`-t` picks the tree in both, and `-c` and `--package` work like in
`beehave graph`: the config applies to both sides. From Python:

```python
import beehave

result = beehave.diff_graphs(beehave.analyze("old.xml").graph, beehave.analyze("new.xml").graph)
print(result.to_markdown())
print(result.score.f1, result.changed)
```
