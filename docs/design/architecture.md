# Architecture

Beehave is a pipeline. A tree file goes in, an action graph comes out. Every
step has one job and one input type, so each can be tested and replaced on its
own.

```mermaid
flowchart LR
    xml[/"BT.CPP XML<br/>(v3 today)"/] --> parse
    parse["1. Parse"] --> model[("Tree model<br/>Document")]
    model --> flatten["2. Flatten"]
    flatten --> flat[("FlatTree")]
    flat --> walk["3. Walk"]
    walk --> graph[("ActionGraph")]
    graph --> render["5. Render"]
    render --> out[/"text · Mermaid · DOT · JSON"/]
    graph --> stats["Stats"]
    simplify["4. Simplify<br/>(Phase 2)"] -.-> graph
```

The design plan names five steps: parse, flatten, walk, simplify, render.
Phase 1 ships four of them. Simplify (shrinking guards with a BDD or
`sympy`) is Phase 2, and the walk already keeps guards in a form it can
consume.

## The steps

| Step | Module | Input | Output | Job |
| --- | --- | --- | --- | --- |
| Parse | `beehave.parsers` | XML files | `Document` | Read every tree, classify every node, check structure. |
| Flatten | `beehave.flatten` | `Document` | `FlatTree` | Inline every subtree, apply port remapping. |
| Walk | `beehave.walk` | `FlatTree` | `ActionGraph` | For each action: what runs next on success, on failure, and under which guard. |
| Render | `beehave.render` | `ActionGraph` | `str` | Text, Mermaid, Graphviz DOT, JSON. |
| Stats | `beehave.stats` | `FlatTree` + `ActionGraph` | `Stats` | Size, reduction, longest guard, breakage. |

`beehave.analyze()` runs parse, flatten and walk in one call. The CLI
(`beehave graph | stats | trees`) is a thin layer over that function.

## One internal model, many parsers

The model (`beehave.model`) does not know about XML or about BT.CPP. A node
has:

- a **kind**: control, decorator, condition, action or subtree;
- a **semantics**: what it does, independent of what a library calls it.
  `SequenceStar` (v3) and `SequenceWithMemory` (v4) are both
  `SEQUENCE_WITH_MEMORY`;
- its **type** as written, its optional **name**, its **ports**, its
  **children**, and where it was read from.

Adding a format (BT.CPP v4, py_trees) means writing a parser that produces
this model. Flatten, walk and render do not change. See
[ADR 0002](adr/0002-one-model-many-parsers.md).

## Parse

`beehave.parsers.btcpp_v3` reads one or more files, follows `<include>`
tags, and reads `<TreeNodesModel>`. It uses expat directly so every node keeps
its line number, and it refuses any `DOCTYPE`, which rules out entity
expansion attacks.

The format is detected from the root element. A file with
`BTCPP_format="4"` is refused with a clear message rather than misread.

A user-defined node is classified by the strongest signal available:

1. the project config (`conditions:` / `actions:` in `beehave.yaml`);
2. the explicit XML form (`<Condition ID="X"/>`);
3. the `<TreeNodesModel>` declaration;
4. its shape: no child is an action, one child a decorator, more a control.

The config wins because it is the only place to fix "conditions in
disguise": nodes registered as actions that only check something.

## Flatten

Every `SubTree` / `SubTreePlus` becomes a subtree node whose single child is
the inlined body. Port values inside the body are rewritten through the
reference's remapping, so a node deep inside nested subtrees shows the
blackboard key it really reads. Keys that are not remapped are private to the
subtree instance and are shown as `{Subtree/key}`.

## Walk

The walk is a continuation-passing compilation. It is described in detail in
[Phase 1](phase-1.md#the-walk) and in
[ADR 0003](adr/0003-continuation-passing-walk.md). In short: compile each node
with "where to go on success" and "where to go on failure", and return "what
runs first". Actions become vertices, conditions become branch points, and
branch points are expanded into guards on the edges.

Nodes that Phase 1 cannot model exactly are walked with a documented
approximation and reported as diagnostics
([ADR 0004](adr/0004-approximate-and-report.md)).

## Render

Renderers are pure functions of the graph. They are deterministic, so the same
tree always gives the same bytes. That lets teams commit graphs next to trees
and review the diff in a pull request.

- **Text**: `A --[failure and not BatteryOK]--> B`, one transition per line.
- **Mermaid**: renders on GitHub, GitLab and in these docs.
- **DOT**: for Graphviz, large graphs and image export.
- **JSON**: a versioned document (`beehave.action-graph`, version 1) for
  other tools, including the future operator view.

Failure edges are always dashed, so the graph still reads in greyscale and for
colour-blind readers.

## Errors and diagnostics

- **Errors** (`beehave.BeehaveError` and subclasses) stop the analysis: the
  input is malformed, a subtree is missing, the format is unsupported. Every
  error carries a `file:line` location when one is known.
- **Diagnostics** do not stop the analysis: an approximated node, an
  include that cannot be followed. They travel with the graph and are printed
  on stderr by the CLI.

## Dependencies

The core needs only the standard library plus PyYAML (for the config file).
See [ADR 0005](adr/0005-python-minimal-dependencies.md).

## Extension points

| You want to… | Touch |
| --- | --- |
| Support a new built-in node | `BUILTINS` in the parser, a `Semantics` member, a rule in `walk.py`, tests. |
| Support a new tree format | A new module in `beehave/parsers/` producing a `Document`. |
| Add an output format | A new module in `beehave/render/` and an entry in `FORMATS`. |
| Add a metric | `beehave/stats.py`. |
