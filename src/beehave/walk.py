"""Walk: turn a flattened tree into an action graph.

The walk is a continuation-passing compilation. Each node is compiled with two
*continuations*: where execution goes when the node succeeds and where it goes
when it fails. Compiling a node returns its *entry*: what runs first when the
node is ticked.

- An action is its own entry; its continuations become its outgoing edges.
- A condition is a branch point: "if it holds, go to the success continuation,
  else to the failure continuation". Branches are expanded into guards on the
  edges, so conditions never become boxes.
- A Sequence chains its children on success, a Fallback on failure.
- An Inverter swaps the continuations; ForceSuccess and ForceFailure merge them.

Nodes whose semantics Phase 1 cannot model exactly (reactive nodes, Parallel,
loops, unknown custom nodes) are walked with a documented approximation and
reported as diagnostics, so the output never silently pretends to be exact.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beehave.diagnostics import Diagnostic
from beehave.graph import (
    FAILURE,
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


_Target = str | _Path | _Branch
"""A terminal vertex ID, the tree path of an action, or a branch point."""

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
    Semantics.WHILE_DO_ELSE: "walked like IfThenElse; the condition is not re-checked",
    Semantics.MANUAL_SELECTOR: "the operator's choice is not modelled; walked like a Fallback",
    Semantics.RETRY: "the retry loop is folded into a note; the loop edge is not shown yet",
    Semantics.REPEAT: "the repeat loop is folded into a note; the loop edge is not shown yet",
    Semantics.KEEP_RUNNING_UNTIL_FAILURE: "walked as transparent; the loop is not shown yet",
}

_SEQUENCES = frozenset(
    {
        Semantics.SEQUENCE,
        Semantics.SEQUENCE_WITH_MEMORY,
        Semantics.REACTIVE_SEQUENCE,
        Semantics.PARALLEL,
    }
)
_FALLBACKS = frozenset({Semantics.FALLBACK, Semantics.REACTIVE_FALLBACK, Semantics.MANUAL_SELECTOR})
_TRANSPARENT = frozenset(
    {
        Semantics.TIMEOUT,
        Semantics.DELAY,
        Semantics.RETRY,
        Semantics.REPEAT,
        Semantics.KEEP_RUNNING_UNTIL_FAILURE,
    }
)
_LOOP_NOTES = {
    Semantics.RETRY: ("retry", "num_attempts"),
    Semantics.REPEAT: ("repeat", "num_cycles"),
}


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
    entry = walker.compile(flat.root, (), SUCCESS, FAILURE, ())
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
    node_diagnostics: list[tuple[_Path, Diagnostic]] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)

    # ------------------------------------------------------------ compile ---

    def compile(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        if node.kind is NodeKind.ACTION:
            return self._action(node, path, s, f, subtrees)
        if node.kind is NodeKind.CONDITION:
            return _Branch(_condition(node), s, f)
        if node.kind is NodeKind.SUBTREE:
            return self.compile(node.children[0], (*path, 0), s, f, (*subtrees, node.ref or ""))

        sem = node.semantics
        if node.kind is NodeKind.CONTROL and sem is Semantics.CUSTOM:
            self._report(
                node, path, "unknown-control", "custom control node is walked like a Sequence"
            )
            return self._sequence(node, path, s, f, subtrees)
        if node.kind is NodeKind.DECORATOR and sem is Semantics.CUSTOM:
            self._report(
                node, path, "unknown-decorator", "custom decorator is treated as transparent"
            )
            return self._child(node, path, s, f, subtrees)

        if sem in _APPROXIMATIONS:
            self._report(node, path, "approximated", _APPROXIMATIONS[sem])
        if sem in _SEQUENCES:
            return self._sequence(node, path, s, f, subtrees)
        if sem in _FALLBACKS:
            return self._fallback(node, path, s, f, subtrees)
        if sem in (Semantics.IF_THEN_ELSE, Semantics.WHILE_DO_ELSE):
            return self._if_then_else(node, path, s, f, subtrees)
        if sem is Semantics.SWITCH:
            return self._switch(node, path, s, f, subtrees)
        if sem is Semantics.INVERTER:
            return self._child(node, path, f, s, subtrees)
        if sem is Semantics.FORCE_SUCCESS:
            return self._child(node, path, s, s, subtrees)
        if sem is Semantics.FORCE_FAILURE:
            return self._child(node, path, f, f, subtrees)
        if sem is Semantics.BLACKBOARD_CHECK:
            return self._blackboard_check(node, path, s, f, subtrees)
        if sem in _LOOP_NOTES:
            self._note_loop(node, path)
        if sem in _TRANSPARENT:
            return self._child(node, path, s, f, subtrees)
        msg = f"no walk rule for {sem}"  # pragma: no cover - every Semantics is handled above
        raise AssertionError(msg)  # pragma: no cover

    def _action(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        if node.semantics in (Semantics.ALWAYS_SUCCESS, Semantics.SET_BLACKBOARD):
            return s
        if node.semantics is Semantics.ALWAYS_FAILURE:
            return f
        self.actions[path] = _ActionInfo(node, subtrees, s, f, self.pending_notes.pop(path, []))
        return path

    def _child(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        return self.compile(node.children[0], (*path, 0), s, f, subtrees)

    def _sequence(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        entry = s
        for index in reversed(range(len(node.children))):
            entry = self.compile(node.children[index], (*path, index), entry, f, subtrees)
        return entry

    def _fallback(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        entry = f
        for index in reversed(range(len(node.children))):
            entry = self.compile(node.children[index], (*path, index), s, entry, subtrees)
        return entry

    def _if_then_else(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        cond, then, *rest = node.children
        then_entry = self.compile(then, (*path, 1), s, f, subtrees)
        else_entry = self.compile(rest[0], (*path, 2), s, f, subtrees) if rest else f
        return self.compile(cond, (*path, 0), then_entry, else_entry, subtrees)

    def _switch(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        variable = node.ports.get("variable", "?")
        last = len(node.children) - 1
        entry = self.compile(node.children[last], (*path, last), s, f, subtrees)
        for index in reversed(range(last)):
            case = node.ports.get(f"case_{index + 1}", "?")
            branch = self.compile(node.children[index], (*path, index), s, f, subtrees)
            entry = _Branch(_equals(variable, case), branch, entry)
        return entry

    def _blackboard_check(
        self, node: Node, path: _Path, s: _Target, f: _Target, subtrees: tuple[str, ...]
    ) -> _Target:
        mismatch = node.ports.get("return_on_mismatch", "FAILURE").strip().upper()
        if mismatch == "RUNNING":
            self._report(node, path, "approximated", "RUNNING on mismatch is walked as FAILURE")
        on_mismatch = s if mismatch == "SUCCESS" else f
        child = self._child(node, path, s, f, subtrees)
        check = _equals(node.ports.get("value_A", "?"), node.ports.get("value_B", "?"))
        return _Branch(check, child, on_mismatch)

    def _note_loop(self, node: Node, path: _Path) -> None:
        child = node.children[0]
        if child.kind is not NodeKind.ACTION or child.semantics is not Semantics.CUSTOM:
            return
        word, port = _LOOP_NOTES[node.semantics]
        count = node.ports.get(port)
        self.pending_notes.setdefault((*path, 0), []).append(f"{word} ×{count}" if count else word)

    def _report(self, node: Node, path: _Path, code: str, message: str) -> None:
        message = f"{node.type}: {message}"
        diagnostic = Diagnostic(code, message, node_type=node.type, location=node.location)
        self.node_diagnostics.append((path, diagnostic))

    # ------------------------------------------------------------- expand ---

    def finish(self, flat: FlatTree, entry: _Target, max_paths: int) -> ActionGraph:
        ids = {path: f"a{n}" for n, path in enumerate(sorted(self.actions), start=1)}

        def vertex_id(target: str | _Path) -> str:
            return target if isinstance(target, str) else ids[target]

        edges: list[Edge] = []

        def add(source: str, outcome: Outcome | None, target: _Target) -> None:
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
        return ActionGraph(
            tree=flat.id,
            format=flat.format,
            vertices=tuple(vertices),
            edges=tuple(edges),
            diagnostics=tuple(d for _, d in sorted(self.node_diagnostics, key=lambda pd: pd[0]))
            + tuple(self.diagnostics),
            node_count=sum(1 for _ in flat.root.walk()),
        )


def _expand(target: _Target, limit: int) -> tuple[list[tuple[Guard, str | _Path]], bool]:
    """Expand branch points into (guard, destination) pairs, in a stable order.

    Contradictory paths (a condition required both to hold and not to hold) are
    dropped, and a condition checked twice on one path appears once.
    """
    results: list[tuple[Guard, str | _Path]] = []
    truncated = False

    def visit(node: _Target, guard: Guard) -> None:
        nonlocal truncated
        if truncated:
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
            if literal.negate() in guard:
                continue
            visit(nxt, guard if literal in guard else (*guard, literal))

    visit(target, ())
    return results, truncated


def _condition(node: Node) -> Condition:
    ports = ", ".join(f"{k}={v}" for k, v in node.ports.items())
    key = f"{node.type}({', '.join(f'{k}={v}' for k, v in sorted(node.ports.items()))})"
    if node.name:
        return Condition(key, node.name)
    return Condition(key, f"{node.type}({ports})" if ports else node.type)


def _equals(left: str, right: str) -> Condition:
    a, b = _display(left), _display(right)
    return Condition(f"{left} == {right}", f"{a} == {b}", f"{a} != {b}")


def _display(value: str) -> str:
    value = value.strip()
    if len(value) > 2 and value[0] == "{" and value[-1] == "}":
        return value[1:-1]
    return value


__all__: Sequence[str] = ["DEFAULT_MAX_PATHS", "build_graph"]
