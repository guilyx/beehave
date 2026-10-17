# Key concepts

Five ideas, in plain words. Only the first three are needed to build and read
the action graph. The last two matter only if we want proofs later.

| Term | What it means here | Needed for |
| --- | --- | --- |
| **Guard** | What must be true for the tree to reach an action, e.g. `BatteryOK and not Emergency`. | Phase 1: the label on each arrow. |
| **Boolean logic** | Writing guards as formulas over condition nodes so they can be simplified. | Phase 2: shrinking guards. |
| **Abstraction** | Hiding control nodes and keeping only actions and the transitions between them. The result is a small state machine. | Phase 1: this is the output. |
| **Temporal logic (LTL)** | Rules about order over time: "always eventually land", "never take off before armed". | Phase 4, optional. |
| **Model checking** | Feeding the abstracted tree and LTL rules to a tool (e.g. nuXmv) that proves or breaks them. | Phase 4, optional. |

## Words used in these docs

**Action graph.** The output of Beehave: one box per action, one arrow per
transition, the guard on the arrow.

**Action.** A leaf that does something: fly, land, resolve a zone.

**Condition.** A leaf that only checks something and returns success or
failure. Conditions never become boxes; they become guards.

**Control node.** A node that decides which child runs: Sequence, Fallback,
IfThenElse… Control nodes disappear in the graph; they become arrows.

**Decorator.** A node with one child that changes how it runs or what it
returns: Inverter, Retry, Timeout…

**Subtree.** A tree used inside another tree. Beehave inlines it.

**Port remapping.** How a subtree's ports connect to its parent's blackboard
(`{key}` entries). Beehave applies it while inlining, so you see the real key.

**Continuation.** Where execution goes after a node ends: one continuation for
success, one for failure. The walk is built on them.

**Diagnostic.** A warning that travels with the graph. It says where the graph
is approximate and why.

**Ontology** (Phase 3). A shared vocabulary for trees: actions, conditions,
zones, mission phases. Each project maps its node types onto it in a small
YAML file, so labels read the same in every tree.
