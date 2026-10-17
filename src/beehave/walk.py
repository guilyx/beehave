"""Walk: turn a flattened tree into an action graph.

The walk is a continuation-passing compilation. Each node is compiled with
three *continuations*: where execution goes when the node succeeds, when it
fails, and when it is skipped. Compiling a node returns its *entry*: what runs
first when the node is ticked.

- An action is its own entry; its continuations become its outgoing edges.
- A condition is a branch point: "if it holds, go to the success continuation,
  else to the failure continuation". Branches are expanded into guards on the
  edges, so conditions never become boxes.
- A Sequence chains its children on success, a Fallback on failure.
- An Inverter swaps the continuations; ForceSuccess and ForceFailure merge them.
- An action that never fails has no failure edge; one that never finishes has
  no outgoing edge at all.

Only BT.CPP v4 nodes can be skipped (by a pre-condition such as ``_skipIf``).
A control node whose children are all skipped is skipped itself, so a
Sequence or a Fallback compiles each child that may skip twice: once for "an
earlier child ran" and once for "every earlier child was skipped". In a tree
where nothing can skip, the skipped continuation is never used.

Nodes whose semantics Phase 1 cannot model exactly (reactive nodes, Parallel,
loops, unknown custom nodes) are walked with a documented approximation and
reported as diagnostics, so the output never silently pretends to be exact.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beehave.diagnostics import Diagnostic, Severity
from beehave.graph import (
    FAILURE,
    SKIPPED,
    START,
    SUCCESS,
    ActionGraph,
    Condition,
    Edge,
    Guard,
    Literal,
    Outcome,
    Vertex,
    VertexKind,
)
from beehave.model import Node, NodeKind, Semantics

if TYPE_CHECKING:
    from collections.abc import Sequence

    from beehave.flatten import FlatTree

DEFAULT_MAX_PATHS = 1024

_Path = tuple[int, ...]


@dataclass(frozen=True, eq=False)
class _Branch:
    condition: Condition
    on_true: _Target
    on_false: _Target


@dataclass(frozen=True, eq=False)
class _Effect:
    """A blackboard write on the way to ``then``.

    Guards checked before a write do not decide checks made after it, because
    the write may have changed what they read.
    """

    then: _Target


_Target = str | _Path | _Branch | _Effect | None
"""A terminal vertex ID, the tree path of an action, a branch point, a write,
or ``None``: no edge at all (BT.CPP would throw there)."""

_APPROXIMATIONS: dict[Semantics, str] = {
    Semantics.REACTIVE_SEQUENCE: (
        "walked like a Sequence; its conditions are re-checked every tick, "
        "but preemption edges are not shown yet"
    ),
    Semantics.REACTIVE_FALLBACK: (
        "walked like a Fallback; its conditions are re-checked every tick, "
        "but preemption edges are not shown yet"
    ),
    Semantics.PARALLEL: "children are shown as if they ran one after another",
    Semantics.PARALLEL_ALL: "children are shown as if they ran one after another",
    Semantics.WHILE_DO_ELSE: "walked like IfThenElse; the condition is not re-checked",
    Semantics.MANUAL_SELECTOR: "the operator's choice is not modelled; walked like a Fallback",
    Semantics.RETRY: "the retry loop is folded into a note; the loop edge is not shown yet",
    Semantics.REPEAT: "the repeat loop is folded into a note; the loop edge is not shown yet",
    Semantics.LOOP_QUEUE: (
        "the loop over the queue is folded into a note; the loop edge is not shown yet"
    ),
    Semantics.KEEP_RUNNING_UNTIL_FAILURE: (
        "never succeeds (a successful child is ticked again); walked as transparent, "
        "the loop is not shown yet"
    ),
    Semantics.TIMEOUT: "can also fail when time runs out; those failure edges are not shown yet",
    Semantics.RUN_ONCE: (
        "after its child completes once, later activations return that result "
        "without running it; those edges are not shown yet"
    ),
}

_SEQUENCES = frozenset(
    {
        Semantics.SEQUENCE,
        Semantics.SEQUENCE_WITH_MEMORY,
        Semantics.REACTIVE_SEQUENCE,
        Semantics.PARALLEL,
        Semantics.PARALLEL_ALL,
    }
)
_FALLBACKS = frozenset({Semantics.FALLBACK, Semantics.REACTIVE_FALLBACK, Semantics.MANUAL_SELECTOR})
_TRANSPARENT = frozenset(
    {
        Semantics.TIMEOUT,
        Semantics.DELAY,
        Semantics.PASS_THROUGH,
        Semantics.RUN_ONCE,
        Semantics.RETRY,
        Semantics.REPEAT,
    }
)
_WRITES = frozenset({Semantics.SET_BLACKBOARD, Semantics.SCRIPT})
_NEVER_FAIL = frozenset({Semantics.ALWAYS_RUNNING, Semantics.WAIT})
# The note word, then the count port of each format (BT.CPP first, then py_trees).
_LOOP_NOTES: dict[Semantics, tuple[str, tuple[str, ...]]] = {
    Semantics.RETRY: ("retry", ("num_attempts", "num_failures")),
    Semantics.REPEAT: ("repeat", ("num_cycles", "num_success")),
    Semantics.LOOP_QUEUE: ("loop", ()),
}
# Pre-conditions, innermost first: the first one BT.CPP checks wraps the others.
_PRE_CONDITIONS = ("_while", "_skipIf", "_successIf", "_failureIf")


def build_graph(flat: FlatTree, *, max_paths: int = DEFAULT_MAX_PATHS) -> ActionGraph:
    """Build the action graph of a flattened tree.

    Args:
        flat: The tree, with subtrees already inlined.
        max_paths: The most guarded transitions to expand out of one action
            outcome. Larger trees are truncated and a diagnostic says so.

    Returns:
        The action graph.
    """
    walker = _Walker()
    entry = walker.compile(flat.root, (), SUCCESS, FAILURE, SKIPPED, ())
    return walker.finish(flat, entry, max_paths)


@dataclass
class _ActionInfo:
    node: Node
    subtrees: tuple[str, ...]
    on_success: _Target
    on_failure: _Target
    notes: list[str] = field(default_factory=list)


@dataclass
class _Walker:
    actions: dict[_Path, _ActionInfo] = field(default_factory=dict)
    pending_notes: dict[_Path, list[str]] = field(default_factory=dict)
    node_diagnostics: dict[tuple[_Path, str, str], Diagnostic] = field(default_factory=dict)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    compiled: dict[tuple[object, ...], _Target] = field(default_factory=dict)
    skippable: dict[int, bool] = field(default_factory=dict)

    # ------------------------------------------------------------ compile ---

    def compile(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        # A child that may be skipped is compiled once per track; the cache
        # makes the parts that do not depend on the track shared.
        key = (path, s, f, k, subtrees)
        if key not in self.compiled:
            body = self._body(node, path, s, f, k, subtrees)
            self.compiled[key] = self._pre_conditions(node, path, body, s, f, k)
        return self.compiled[key]

    def _pre_conditions(
        self, node: Node, path: _Path, entry: _Target, s: _Target, f: _Target, k: _Target
    ) -> _Target:
        scripts = node.scripts
        if "_while" in scripts:
            self._report(
                node,
                path,
                "approximated",
                "_while is checked on every tick; the interrupt edges are not shown yet",
            )
        outcomes = {"_while": k, "_skipIf": k, "_successIf": s, "_failureIf": f}
        for attribute in _PRE_CONDITIONS:
            if attribute in scripts:
                check = _script(scripts[attribute])
                if attribute == "_while":  # holds: run the node; does not hold: skip it
                    entry = _Branch(check, entry, k)
                else:
                    entry = _Branch(check, outcomes[attribute], entry)
        return entry

    def _body(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        if node.kind is NodeKind.ACTION:
            return self._action(node, path, s, f, subtrees)
        if node.kind is NodeKind.CONDITION:
            return _Branch(self._condition(node, path), s, f)
        if node.kind is NodeKind.SUBTREE:
            return self.compile(node.children[0], (*path, 0), s, f, k, (*subtrees, node.ref or ""))

        sem = node.semantics
        if node.kind is NodeKind.CONTROL and sem is Semantics.CUSTOM:
            self._report(
                node, path, "unknown-control", "custom control node is walked like a Sequence"
            )
            return self._sequence(node, path, s, f, k, subtrees)
        if node.kind is NodeKind.DECORATOR and sem is Semantics.CUSTOM:
            self._report(
                node, path, "unknown-decorator", "custom decorator is treated as transparent"
            )
            return self._child(node, path, s, f, k, subtrees)

        if sem in _APPROXIMATIONS:
            self._report(node, path, "approximated", _APPROXIMATIONS[sem])
        if sem in _LOOP_NOTES:
            self._note_loop(node, path)
        if sem in _SEQUENCES:
            return self._sequence(
                node, path, s, f, k, subtrees, all_skipped=self._all_skipped(node, s, k)
            )
        if sem in _FALLBACKS:
            return self._fallback(node, path, s, f, k, subtrees)
        if sem in (Semantics.IF_THEN_ELSE, Semantics.WHILE_DO_ELSE):
            return self._if_then_else(node, path, s, f, k, subtrees)
        if sem is Semantics.SWITCH:
            return self._switch(node, path, s, f, k, subtrees)
        if sem is Semantics.TRY_CATCH:
            return self._try_catch(node, path, s, f, k, subtrees)
        if sem is Semantics.INVERTER:
            return self._child(node, path, f, s, k, subtrees)
        if sem is Semantics.FORCE_SUCCESS:
            return self._child(node, path, s, s, k, subtrees)
        if sem is Semantics.FORCE_FAILURE:
            return self._child(node, path, f, f, k, subtrees)
        if sem is Semantics.KEEP_RUNNING_UNTIL_FAILURE:
            # A skipped child is ticked again, like a successful one.
            return self._child(node, path, s, f, s, subtrees)
        if sem is Semantics.BLACKBOARD_CHECK:
            return self._blackboard_check(node, path, s, f, k, subtrees)
        if sem is Semantics.STATUS_MAP:
            return self._status_map(node, path, s, f, k, subtrees)
        if sem is Semantics.PRECONDITION:
            return self._precondition(node, path, s, f, k, subtrees)
        if sem is Semantics.SKIP_UNLESS_UPDATED:
            child = self._child(node, path, s, f, k, subtrees)
            return _Branch(_updated(node, path), child, k)
        if sem is Semantics.LOOP_QUEUE:
            return self._loop_queue(node, path, s, f, k, subtrees)
        if sem in _TRANSPARENT:
            return self._child(node, path, s, f, k, subtrees)
        msg = f"no walk rule for {sem}"  # pragma: no cover - every Semantics is handled above
        raise AssertionError(msg)  # pragma: no cover

    def _action(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        if node.semantics is Semantics.ALWAYS_SUCCESS:
            return s
        if node.semantics in _WRITES:
            return _Effect(s)
        if node.semantics is Semantics.ALWAYS_FAILURE:
            return f
        on_success = None if node.semantics is Semantics.ALWAYS_RUNNING else s
        on_failure = None if node.semantics in _NEVER_FAIL else f
        known = self.actions.get(path)
        if known is not None and (known.on_success, known.on_failure) != (on_success, on_failure):
            # Only a loop over a skippable child gets here: its outcome depends
            # on whether the siblings before it ran.
            self._report(
                node,
                path,
                "approximated",
                "what follows depends on whether earlier siblings were skipped; "
                "only one case is drawn",
            )
            return path
        notes = self.pending_notes.pop(path, known.notes if known else [])
        self.actions[path] = _ActionInfo(node, subtrees, on_success, on_failure, notes)
        return path

    def _child(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        return self.compile(node.children[0], (*path, 0), s, f, k, subtrees)

    def _sequence(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
        *,
        all_skipped: _Target | None = None,
        count: int | None = None,
    ) -> _Target:
        # Two tracks: `ran` once some child has run (later skips lead to
        # success), `skipped` while every child so far was skipped.
        ran, skipped = s, k if all_skipped is None else all_skipped
        for index in reversed(range(len(node.children) if count is None else count)):
            child = node.children[index]
            entry = self.compile(child, (*path, index), ran, f, ran, subtrees)
            if self._may_skip(child):
                skipped = self.compile(child, (*path, index), ran, f, skipped, subtrees)
            else:
                skipped = entry
            ran = entry
        return skipped

    def _fallback(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        ran, skipped = f, k
        for index in reversed(range(len(node.children))):
            child = node.children[index]
            entry = self.compile(child, (*path, index), s, ran, ran, subtrees)
            if self._may_skip(child):
                skipped = self.compile(child, (*path, index), s, ran, skipped, subtrees)
            else:
                skipped = entry
            ran = entry
        return skipped

    def _all_skipped(self, node: Node, s: _Target, k: _Target) -> _Target:
        # BT.CPP's Parallel counts skipped children as successes unless
        # success_count is positive.
        if node.semantics is Semantics.PARALLEL and not _positive(node.ports.get("success_count")):
            return s
        return k

    def _if_then_else(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        cond, then, *rest = node.children
        then_entry = self.compile(then, (*path, 1), s, f, k, subtrees)
        else_entry = self.compile(rest[0], (*path, 2), s, f, k, subtrees) if rest else f
        if self._may_skip(cond):
            self._error(node, path, "a skipped first child makes BT.CPP throw; no edge is drawn")
        return self.compile(cond, (*path, 0), then_entry, else_entry, None, subtrees)

    def _switch(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        variable = node.ports.get("variable")
        last = len(node.children) - 1
        entry = self.compile(node.children[last], (*path, last), s, f, k, subtrees)
        default = entry
        for index in reversed(range(last)):
            case = node.ports.get(f"case_{index + 1}", "?")
            branch = self.compile(node.children[index], (*path, index), s, f, k, subtrees)
            entry = _Branch(_equals(variable or "", case), branch, entry)
        # Without a variable, BT.CPP always runs the default child.
        return entry if variable is not None else default

    def _try_catch(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        # The last child is the catch block: it runs after a failure, and the
        # node fails whatever it returns.
        last = len(node.children) - 1
        catch = self.compile(node.children[last], (*path, last), f, f, f, subtrees)
        return self._sequence(node, path, s, catch, k, subtrees, count=last)

    def _blackboard_check(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        mismatch = node.ports.get("return_on_mismatch", "FAILURE").strip().upper()
        if mismatch == "RUNNING":
            self._report(node, path, "approximated", "RUNNING on mismatch is walked as FAILURE")
        on_mismatch = s if mismatch == "SUCCESS" else f
        child = self._child(node, path, s, f, k, subtrees)
        check = _equals(node.ports.get("value_A", "?"), node.ports.get("value_B", "?"))
        return _Branch(check, child, on_mismatch)

    def _status_map(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        on_success = node.ports.get("on_success", "SUCCESS").strip().upper()
        on_failure = node.ports.get("on_failure", "FAILURE").strip().upper()
        on_running = node.ports.get("on_running", "RUNNING").strip().upper()
        notes = []
        if on_success == "RUNNING":
            notes.append("a successful child is ticked again")
        if on_failure == "RUNNING":
            notes.append("a failed child is ticked again")
        loops = bool(notes)
        halts = on_running != "RUNNING"
        if halts:
            notes.append(f"a RUNNING child is halted and counts as {on_running}")
        if notes:
            hidden = (
                "the loop and those edges are"
                if loops and halts
                else ("the loop is" if loops else "those edges are")
            )
            self._report(node, path, "approximated", f"{'; '.join(notes)}; {hidden} not shown yet")
        # Phase 1 walks "tick it again" as if the child's own result went through.
        targets = {"SUCCESS": s, "FAILURE": f}
        return self._child(
            node, path, targets.get(on_success, s), targets.get(on_failure, f), k, subtrees
        )

    def _precondition(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        otherwise = node.ports.get("else", "FAILURE").strip().upper()
        targets = {"SUCCESS": s, "FAILURE": f, "SKIPPED": k}
        if otherwise == "RUNNING":
            fallback: _Target = None  # it waits until the script holds
        elif otherwise in targets:
            fallback = targets[otherwise]
        else:
            self._error(node, path, f'else="{otherwise}" makes BT.CPP throw; no edge is drawn')
            fallback = None
        child = self._child(node, path, s, f, k, subtrees)
        return _Branch(_script(node.ports.get("if", "true")), child, fallback)

    def _loop_queue(
        self,
        node: Node,
        path: _Path,
        s: _Target,
        f: _Target,
        k: _Target,
        subtrees: tuple[str, ...],
    ) -> _Target:
        # Phase 1 folds the loop: after the child, the queue is taken as empty.
        otherwise = node.ports.get("if_empty", "SUCCESS").strip().upper()
        empty = {"SUCCESS": s, "FAILURE": f, "SKIPPED": k}.get(otherwise, s)
        child = self._child(node, path, empty, f, empty, subtrees)
        queue = _display(node.ports.get("queue", "queue"))
        has_items = Condition(f"{node.type}@{_dotted(path)}", f"{queue} has items")
        return _Branch(has_items, child, empty)

    def _condition(self, node: Node, path: _Path) -> Condition:
        if node.semantics is Semantics.SCRIPT_CONDITION:
            return _script(node.ports.get("code", "true"))
        if node.semantics is Semantics.ENTRY_UPDATED:
            return _updated(node, path)
        return _condition(node)

    def _may_skip(self, node: Node) -> bool:
        known = self.skippable.get(id(node))
        if known is None:
            known = self.skippable[id(node)] = self._can_skip(node)
        return known

    def _can_skip(self, node: Node) -> bool:
        if "_skipIf" in node.scripts or "_while" in node.scripts:
            return True
        sem, children = node.semantics, node.children
        if not children or sem is Semantics.KEEP_RUNNING_UNTIL_FAILURE:
            return False
        if sem is Semantics.SKIP_UNLESS_UPDATED:
            return True
        if sem is Semantics.PRECONDITION:
            skips = node.ports.get("else", "").strip().upper() == "SKIPPED"
            return skips or self._may_skip(children[0])
        if sem is Semantics.LOOP_QUEUE:
            return node.ports.get("if_empty", "").strip().upper() == "SKIPPED"
        if sem in (Semantics.IF_THEN_ELSE, Semantics.WHILE_DO_ELSE):
            return any(self._may_skip(c) for c in children[1:])
        if sem is Semantics.SWITCH:
            return any(self._may_skip(c) for c in children)
        if sem is Semantics.TRY_CATCH:
            return all(self._may_skip(c) for c in children[:-1])
        if sem is Semantics.PARALLEL and not _positive(node.ports.get("success_count")):
            return False
        return all(self._may_skip(c) for c in children)

    def _note_loop(self, node: Node, path: _Path) -> None:
        child = node.children[0]
        if child.kind is not NodeKind.ACTION or child.semantics is not Semantics.CUSTOM:
            return
        word, ports = _LOOP_NOTES[node.semantics]
        count = next((node.ports[p] for p in ports if p in node.ports), None)
        self.pending_notes.setdefault((*path, 0), []).append(f"{word} ×{count}" if count else word)

    def _error(self, node: Node, path: _Path, message: str) -> None:
        self._report(node, path, "runtime-error", message, Severity.ERROR)

    def _report(
        self,
        node: Node,
        path: _Path,
        code: str,
        message: str,
        severity: Severity = Severity.WARNING,
    ) -> None:
        named = node.name and node.name != node.type
        message = f'{node.type} "{node.name}": {message}' if named else f"{node.type}: {message}"
        diagnostic = Diagnostic(code, message, severity, node.type, node.location)
        self.node_diagnostics.setdefault((path, code, message), diagnostic)

    # ------------------------------------------------------------- expand ---

    def finish(self, flat: FlatTree, entry: _Target, max_paths: int) -> ActionGraph:
        ids = {path: f"a{n}" for n, path in enumerate(sorted(self.actions), start=1)}

        def vertex_id(target: str | _Path) -> str:
            return target if isinstance(target, str) else ids[target]

        edges: list[Edge] = []

        def add(source: str, outcome: Outcome | None, target: _Target) -> None:
            if target is None:
                return
            paths, truncated = _expand(target, max_paths)
            edges.extend(Edge(source, vertex_id(t), outcome, guard) for guard, t in paths)
            if truncated:
                self.diagnostics.append(
                    Diagnostic(
                        "too-many-paths",
                        f"more than {max_paths} guarded transitions leave '{source}'; "
                        "the rest are not shown",
                    )
                )

        add(START, None, entry)
        vertices = [Vertex(START, VertexKind.START, "START")]
        for path in sorted(self.actions):
            info = self.actions[path]
            node = info.node
            vertices.append(
                Vertex(
                    ids[path],
                    VertexKind.ACTION,
                    node.label,
                    node.type,
                    dict(node.ports),
                    tuple(info.notes),
                    info.subtrees,
                    node.location,
                )
            )
            add(ids[path], Outcome.SUCCESS, info.on_success)
            add(ids[path], Outcome.FAILURE, info.on_failure)
        vertices += [
            Vertex(SUCCESS, VertexKind.SUCCESS, "SUCCESS"),
            Vertex(FAILURE, VertexKind.FAILURE, "FAILURE"),
        ]
        if any(edge.target == SKIPPED for edge in edges):
            vertices.append(Vertex(SKIPPED, VertexKind.SKIPPED, "SKIPPED"))
        by_path = sorted(self.node_diagnostics.items(), key=lambda item: item[0][0])
        return ActionGraph(
            tree=flat.id,
            format=flat.format,
            vertices=tuple(vertices),
            edges=tuple(edges),
            diagnostics=(flat.diagnostics + tuple(d for _, d in by_path) + tuple(self.diagnostics)),
            node_count=sum(1 for _ in flat.root.walk()),
        )


def _expand(target: _Target, limit: int) -> tuple[list[tuple[Guard, str | _Path]], bool]:
    """Expand branch points into (guard, destination) pairs, in a stable order.

    Contradictory paths (a condition required both to hold and not to hold) are
    dropped, and a condition checked twice on one path appears once. A write to
    the blackboard ends what earlier checks decide.
    """
    results: list[tuple[Guard, str | _Path]] = []
    truncated = False

    def visit(node: _Target, guard: Guard, known: frozenset[Literal]) -> None:
        nonlocal truncated
        if truncated or node is None:
            return
        if isinstance(node, _Effect):
            visit(node.then, guard, frozenset())
            return
        if not isinstance(node, _Branch):
            if len(results) == limit:
                truncated = True
                return
            results.append((guard, node))
            return
        for literal, nxt in (
            (Literal(node.condition, True), node.on_true),
            (Literal(node.condition, False), node.on_false),
        ):
            if literal.negate() in known:
                continue
            visit(nxt, guard if literal in guard else (*guard, literal), known | {literal})

    visit(target, (), frozenset())
    return results, truncated


def _condition(node: Node) -> Condition:
    if node.semantics is Semantics.BLACKBOARD_CONDITION:
        expression = node.ports.get("expression", node.label)
        return Condition(expression, expression)
    ports = ", ".join(f"{k}={v}" for k, v in node.ports.items())
    key = f"{node.type}({', '.join(f'{k}={v}' for k, v in sorted(node.ports.items()))})"
    if node.name:
        # The name is part of the identity: in py_trees it is often the only
        # thing that tells two instances of one class apart.
        return Condition(f'{key} "{node.name}"', node.name)
    return Condition(key, f"{node.type}({ports})" if ports else node.type)


_NAME = re.compile(r"!?[A-Za-z_@][\w@/#]*")


def _script(code: str) -> Condition:
    """A condition written as a BT.CPP script, e.g. ``battery < 20``.

    Whitespace never changes what a script means, so it is not part of the key.
    The negation is written the way BT.CPP would: ``!ready``, ``!(battery < 20)``.
    """
    label = " ".join(code.split())
    if _NAME.fullmatch(label):
        negated = label[1:] if label.startswith("!") else f"!{label}"
    else:
        negated = f"!({label})"
    return Condition("".join(code.split()), label, negated)


def _updated(node: Node, path: _Path) -> Condition:
    # Each node remembers the version of the entry it saw last, so the check
    # belongs to the node: two nodes watching one entry are two conditions.
    entry = _display(node.ports.get("entry", "entry"))
    return Condition(f"{node.type}@{_dotted(path)}", f"{entry} updated")


def _equals(left: str, right: str) -> Condition:
    a, b = _display(left), _display(right)
    return Condition(f"{left} == {right}", f"{a} == {b}", f"{a} != {b}")


def _display(value: str) -> str:
    value = value.strip()
    if len(value) > 2 and value[0] == "{" and value[-1] == "}":
        return value[1:-1]
    return value


def _dotted(path: _Path) -> str:
    return ".".join(map(str, path))


def _positive(value: str | None) -> bool:
    try:
        return value is not None and int(value) > 0
    except ValueError:
        return False


__all__: Sequence[str] = ["DEFAULT_MAX_PATHS", "build_graph"]
