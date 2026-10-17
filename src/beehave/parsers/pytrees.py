"""Read a live py_trees tree.

A py_trees tree is built in Python, so there is no file to parse: the adapter
walks the objects that a factory function returns and turns them into the
shared model. It only reads attributes. It never calls ``setup()``, ``tick()``,
an ``EternalGuard`` condition or a callable comparison value, so converting a
tree runs none of its code.

Importing the module that builds the tree does run code: that is what
:func:`load_py_trees` is for, and it is always an explicit choice.

py_trees is an optional dependency (``pip install 'beehave-bt[py-trees]'``).
It is imported when a function here is first called, never when Beehave is.
"""

from __future__ import annotations

import enum
import functools
import importlib.util
import operator
import pkgutil
import re
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

from beehave.config import Config
from beehave.diagnostics import Diagnostic
from beehave.errors import BeehaveError, ParseError, UnsupportedFormatError
from beehave.model import Document, Node, NodeKind, Semantics, Tree

if TYPE_CHECKING:
    from collections.abc import Callable
    from types import ModuleType

FORMAT = "py_trees"
MIN_VERSION = (2, 2)
_INSTALL = "pip install 'beehave-bt[py-trees]'"

# What a node is, read from the py_trees object: kind, semantics and ports.
_Reading = tuple[NodeKind, Semantics, dict[str, str]]

_SYMBOLS: dict[Callable[..., Any], str] = {
    operator.lt: "<",
    operator.le: "<=",
    operator.eq: "==",
    operator.ne: "!=",
    operator.ge: ">=",
    operator.gt: ">",
}
_WORDS: dict[Callable[..., Any], str] = {
    operator.and_: "and",
    operator.or_: "or",
    operator.xor: "xor",
}


def from_py_trees(tree: object, *, config: Config | None = None) -> Document:
    """Convert a py_trees tree to the shared model.

    Args:
        tree: The root ``Behaviour``, or a ``BehaviourTree`` (including
            py_trees_ros's), whose ``root`` is used.
        config: Project settings: which user behaviour classes are conditions.
            A class is named by ``__name__`` or by ``module.QualName``, and
            naming a base class covers every class derived from it.

    Returns:
        A document with one tree, named after the root, as its main tree.

    Raises:
        UnsupportedFormatError: If py_trees is missing or older than 2.2.
        ParseError: If one node appears twice in the tree.
        BeehaveError: If ``tree`` is not a py_trees tree.

    Example:
        >>> import beehave
        >>> document = beehave.from_py_trees(create_root())  # doctest: +SKIP
    """
    py_trees = _require_py_trees()
    if isinstance(tree, py_trees.trees.BehaviourTree):
        tree = tree.root
    if not isinstance(tree, py_trees.behaviour.Behaviour):
        msg = f"expected a py_trees Behaviour or BehaviourTree, got {type(tree).__name__}"
        raise BeehaveError(msg)
    adapter = _Adapter(py_trees, config or Config())
    root = adapter.node(tree)
    tree_id = _clean(tree.name)
    return Document(FORMAT, {tree_id: Tree(tree_id, root)}, tree_id, tuple(adapter.diagnostics))


def load_py_trees(spec: str, **kwargs: Any) -> Any:
    """Import a py_trees factory and call it; this runs the code of its module.

    Args:
        spec: ``package.module:function`` or ``path/to/file.py:function``.
            ``package.module.function`` works too, as in ``py-trees-render``.
            The working directory (for a module) or the file's directory (for a
            file) is put first on ``sys.path``, so sibling imports work.
        **kwargs: Arguments for the factory.

    Returns:
        What the factory returns, or the object itself when ``spec`` names a
        ``Behaviour`` or ``BehaviourTree`` instead of a function.

    Raises:
        ParseError: If the module cannot be imported or the factory raises.
        BeehaveError: If ``spec`` names something that is not a tree or a factory.
    """
    py_trees = _require_py_trees()
    target = _resolve(spec)
    if isinstance(target, (py_trees.behaviour.Behaviour, py_trees.trees.BehaviourTree)):
        if kwargs:
            msg = f"{spec} is a tree, not a function: it takes no arguments"
            raise BeehaveError(msg)
        return target
    if not callable(target):
        msg = f"{spec} is neither a py_trees tree nor a function that builds one"
        raise BeehaveError(msg)
    try:
        return target(**kwargs)
    except Exception as exc:
        msg = f"calling {spec} raised {type(exc).__name__}: {exc}"
        raise ParseError(msg) from exc


# ---------------------------------------------------------------- loading ---


def _require_py_trees() -> ModuleType:
    try:
        import py_trees  # noqa: PLC0415 - optional dependency
    except ImportError as exc:
        msg = f"the py_trees adapter needs py_trees >= 2.2: {_INSTALL}"
        raise UnsupportedFormatError(msg) from exc
    found = str(py_trees.version.__version__)
    if tuple(int(part) for part in re.findall(r"\d+", found)[:2]) < MIN_VERSION:
        msg = f"the py_trees adapter needs py_trees >= 2.2, found {found}: {_INSTALL}"
        raise UnsupportedFormatError(msg)
    return py_trees


def _resolve(spec: str) -> Any:
    module, sep, attr = spec.rpartition(":")
    if sep and module.endswith(".py"):
        return _from_file(Path(module), attr, spec)
    if not spec or spec.startswith((":", ".")):
        msg = f"expected package.module:function or file.py:function, got {spec!r}"
        raise BeehaveError(msg)
    _prepend(Path.cwd())
    try:
        return pkgutil.resolve_name(spec)
    except (ImportError, AttributeError, ValueError) as exc:
        msg = f"cannot import {spec}: {type(exc).__name__}: {exc}"
        raise ParseError(msg) from exc
    except Exception as exc:
        msg = f"importing {spec} raised {type(exc).__name__}: {exc}"
        raise ParseError(msg) from exc


def _from_file(path: Path, attr: str, spec: str) -> Any:
    if not path.is_file():
        msg = f"cannot read {path.as_posix()}: no such file"
        raise ParseError(msg)
    path = path.resolve()
    _prepend(path.parent)
    name = path.stem if path.stem not in sys.modules else f"_beehave_{path.stem}"
    module_spec = importlib.util.spec_from_file_location(name, path)
    if module_spec is None or module_spec.loader is None:  # pragma: no cover - .py files load
        msg = f"cannot import {path.as_posix()}"
        raise ParseError(msg)
    module = importlib.util.module_from_spec(module_spec)
    sys.modules[name] = module
    try:
        module_spec.loader.exec_module(module)
    except Exception as exc:
        del sys.modules[name]
        msg = f"importing {path.as_posix()} raised {type(exc).__name__}: {exc}"
        raise ParseError(msg) from exc
    target: Any = module
    for part in attr.split("."):
        if not hasattr(target, part):
            msg = f"cannot import {spec}: {path.name} has no attribute {attr!r}"
            raise ParseError(msg)
        target = getattr(target, part)
    return target


def _prepend(directory: Path) -> None:
    entry = str(directory)
    if entry not in sys.path:
        sys.path.insert(0, entry)


# ---------------------------------------------------------------- adapter ---


def _owner(cls: type) -> type:
    """The nearest class in the MRO that defines the tick logic.

    Looking classes up by owner, not with ``isinstance``, tells ``WaitFor…``
    apart from the ``Check…`` class it subclasses, and still recognises a user
    subclass that only changes ``__init__``.
    """
    return next((k for k in cls.__mro__ if "tick" in vars(k) or "update" in vars(k)), cls)


def _clean(name: object) -> str:
    # Names built by py_trees idioms contain newlines ("Mark\ntask_done").
    return " ".join(line.strip() for line in str(name).splitlines())


class _Adapter:
    def __init__(self, py_trees: ModuleType, config: Config) -> None:
        self.py_trees = py_trees
        self.config = config
        self.seen: set[int] = set()
        self.diagnostics: list[Diagnostic] = []
        self.decorators = _decorator_rules(py_trees)
        self.leaves = _leaf_rules(py_trees)

    def node(self, behaviour: Any) -> Node:
        name = _clean(behaviour.name)
        if id(behaviour) in self.seen:
            msg = f"'{name}' appears twice in the tree; a py_trees node can have only one parent"
            raise ParseError(msg)
        self.seen.add(id(behaviour))
        owner = _owner(type(behaviour))
        if isinstance(behaviour, self.py_trees.composites.Composite):
            return self._composite(behaviour, owner, name)
        if isinstance(behaviour, self.py_trees.decorators.Decorator):
            return self._decorator(behaviour, owner, name)
        if behaviour.children:
            # A hand-made composite: the walk reports it as an unknown control.
            children = tuple(self.node(child) for child in behaviour.children)
            return Node(NodeKind.CONTROL, type(behaviour).__name__, name=name, children=children)
        return self._leaf(behaviour, owner, name)

    def _composite(self, composite: Any, owner: type, name: str) -> Node:
        composites = self.py_trees.composites
        children = tuple(self.node(child) for child in composite.children)
        type_ = type(composite).__name__
        semantics, ports = Semantics.CUSTOM, {}
        if owner in (composites.Sequence, composites.Selector):
            memory = bool(composite.memory)
            type_ = f"{type_}(memory={memory})"
            if owner is composites.Sequence:
                semantics = Semantics.SEQUENCE if memory else Semantics.REACTIVE_SEQUENCE
            else:
                semantics = Semantics.FALLBACK if memory else Semantics.REACTIVE_FALLBACK
        elif owner is composites.Parallel:
            semantics, ports = Semantics.PARALLEL, _parallel_ports(composite)
        return Node(NodeKind.CONTROL, type_, semantics, name, ports, children)

    def _decorator(self, decorator: Any, owner: type, name: str) -> Node:
        if owner is self.py_trees.decorators.EternalGuard:
            return self._eternal_guard(decorator, name)
        child = self.node(decorator.decorated)
        rule = self.decorators.get(owner)
        semantics, ports = rule(decorator) if rule else (Semantics.CUSTOM, {})
        return Node(NodeKind.DECORATOR, type(decorator).__name__, semantics, name, ports, (child,))

    def _eternal_guard(self, guard: Any, name: str) -> Node:
        # EternalGuard checks its condition before every tick of its child,
        # which is what a reactive sequence over [condition, child] does.
        condition = guard.condition
        if isinstance(condition, functools.partial):
            condition = condition.func
        keys = sorted(key.lstrip("/") for key in guard.blackboard.read)
        check = Node(
            NodeKind.CONDITION,
            getattr(condition, "__name__", type(condition).__name__),
            name=name,
            ports={"blackboard_keys": ", ".join(keys)} if keys else {},
        )
        child = self.node(guard.decorated)
        return Node(
            NodeKind.CONTROL,
            type(guard).__name__,
            Semantics.REACTIVE_SEQUENCE,
            name,
            children=(check, child),
        )

    def _leaf(self, leaf: Any, owner: type, name: str) -> Node:
        type_ = type(leaf).__name__
        rule = self.leaves.get(owner)
        kind, semantics, ports = rule(leaf) if rule else (NodeKind.ACTION, Semantics.CUSTOM, {})
        if semantics is Semantics.CUSTOM:
            kind = self._configured(type(leaf), kind)
        if owner is getattr(self.py_trees.behaviours, "BlackboardToStatus", None):
            message = (
                f'{type_} "{name}": returns the status stored in {leaf.variable_name}, '
                "RUNNING included; walked as a condition"
            )
            self.diagnostics.append(Diagnostic("approximated", message, node_type=type_))
        return Node(kind, type_, semantics, name, ports)

    def _configured(self, cls: type, default: NodeKind) -> NodeKind:
        # The config may name the class or any of its bases; the nearest wins.
        for klass in cls.__mro__:
            names = {klass.__name__, f"{klass.__module__}.{klass.__qualname__}"}
            if names & self.config.conditions:
                return NodeKind.CONDITION
            if names & self.config.actions:
                return NodeKind.ACTION
        return default


# ------------------------------------------------------------------ rules ---


def _decorator_rules(
    py_trees: ModuleType,
) -> dict[type, Callable[[Any], tuple[Semantics, dict[str, str]]]]:
    d = py_trees.decorators
    status = py_trees.common.Status

    def fixed(semantics: Semantics) -> Callable[[Any], tuple[Semantics, dict[str, str]]]:
        return lambda _: (semantics, {})

    def status_map(
        on_success: str, on_failure: str, on_running: str
    ) -> tuple[Semantics, dict[str, str]]:
        ports = {"on_success": on_success, "on_failure": on_failure, "on_running": on_running}
        return Semantics.STATUS_MAP, ports

    def condition(decorator: Any) -> tuple[Semantics, dict[str, str]]:
        wanted = decorator.succeed_status
        if wanted == status.SUCCESS:  # tick until SUCCESS: an unbounded retry
            return Semantics.RETRY, {}
        if wanted == status.FAILURE:
            return status_map("RUNNING", "SUCCESS", "RUNNING")
        return status_map("RUNNING", "RUNNING", "SUCCESS")

    rules: dict[str, Callable[[Any], tuple[Semantics, dict[str, str]]]] = {
        "Inverter": fixed(Semantics.INVERTER),
        "SuccessIsFailure": fixed(Semantics.FORCE_FAILURE),
        "FailureIsSuccess": fixed(Semantics.FORCE_SUCCESS),
        "SuccessIsRunning": fixed(Semantics.KEEP_RUNNING_UNTIL_FAILURE),
        "FailureIsRunning": fixed(Semantics.RETRY),
        "RunningIsFailure": lambda _: status_map("SUCCESS", "FAILURE", "FAILURE"),
        "RunningIsSuccess": lambda _: status_map("SUCCESS", "FAILURE", "SUCCESS"),
        "Condition": condition,
        "Retry": lambda x: (Semantics.RETRY, {"num_failures": str(x.num_failures)}),
        "Repeat": lambda x: (Semantics.REPEAT, {"num_success": str(x.num_success)}),
        "Timeout": lambda x: (Semantics.TIMEOUT, {"duration": str(x.duration)}),
        "OneShot": lambda x: (Semantics.RUN_ONCE, {"policy": x.policy.name}),
        "PassThrough": fixed(Semantics.PASS_THROUGH),
        "Count": fixed(Semantics.PASS_THROUGH),
        "StatusToBlackboard": lambda x: (
            Semantics.PASS_THROUGH,
            {"variable_name": x.variable_name},
        ),
        "ForEach": lambda x: (
            Semantics.REPEAT,
            {"source_key": x.source_key, "target_key": x.target_key},
        ),
    }
    return _by_class(d, rules)


def _leaf_rules(py_trees: ModuleType) -> dict[type, Callable[[Any], _Reading]]:
    action, condition = NodeKind.ACTION, NodeKind.CONDITION

    def fixed(kind: NodeKind, semantics: Semantics) -> Callable[[Any], _Reading]:
        return lambda _: (kind, semantics, {})

    def set_variable(leaf: Any) -> _Reading:
        # With overwrite=False it fails when the variable already exists.
        semantics = Semantics.SET_BLACKBOARD if leaf.overwrite else Semantics.CUSTOM
        return action, semantics, {"variable_name": leaf.variable_name}

    def check(
        kind: NodeKind, semantics: Semantics, text: Callable[[Any], str]
    ) -> Callable[[Any], _Reading]:
        return lambda leaf: (kind, semantics, {"expression": text(leaf)})

    is_set: Callable[[Any], str] = lambda leaf: f"{leaf.variable_name} is set"  # noqa: E731
    holds: Callable[[Any], str] = lambda leaf: _comparison(leaf.check)  # noqa: E731
    bb = Semantics.BLACKBOARD_CONDITION
    rules: dict[str, Callable[[Any], _Reading]] = {
        "Success": fixed(action, Semantics.ALWAYS_SUCCESS),
        "Failure": fixed(action, Semantics.ALWAYS_FAILURE),
        "Running": fixed(action, Semantics.ALWAYS_RUNNING),
        "Dummy": fixed(action, Semantics.ALWAYS_RUNNING),
        "SetBlackboardVariable": set_variable,
        "UnsetBlackboardVariable": lambda x: (action, Semantics.SET_BLACKBOARD, {"key": x.key}),
        "CheckBlackboardVariableExists": check(condition, bb, is_set),
        "CheckBlackboardVariableValue": check(condition, bb, holds),
        "CheckBlackboardVariableValues": check(condition, bb, _joined),
        "CompareBlackboardVariables": check(
            condition, bb, lambda x: _binary(x.operator, x.var1_key, x.var2_key)
        ),
        "WaitForBlackboardVariable": check(action, Semantics.WAIT, is_set),
        "WaitForBlackboardVariableValue": check(action, Semantics.WAIT, holds),
        "SuccessEveryN": lambda x: (condition, Semantics.CUSTOM, {"every_n": str(x.every_n)}),
        "BlackboardToStatus": lambda x: (
            condition,
            Semantics.CUSTOM,
            {"variable_name": x.variable_name},
        ),
        "Periodic": lambda x: (action, Semantics.CUSTOM, {"period": str(x.period)}),
        "TickCounter": lambda x: (
            action,
            Semantics.CUSTOM,
            {"duration": str(x.duration), "completion_status": x.completion_status.name},
        ),
    }
    table = _by_class(py_trees.behaviours, rules)
    table[py_trees.timers.Timer] = lambda x: (action, Semantics.WAIT, {"duration": str(x.duration)})
    return table


def _by_class(module: ModuleType, rules: dict[str, Any]) -> dict[type, Any]:
    # Classes added after py_trees 2.2 (ForEach, CompareBlackboardVariables…)
    # are simply absent from older versions.
    return {getattr(module, name): rule for name, rule in rules.items() if hasattr(module, name)}


def _parallel_ports(parallel: Any) -> dict[str, str]:
    policy = parallel.policy
    ports = {
        "policy": type(policy).__name__,
        "synchronise": str(bool(getattr(policy, "synchronise", False))).lower(),
    }
    selected = getattr(policy, "children", None)
    if selected is not None:
        indices = [
            str(i) for i, child in enumerate(parallel.children) if any(child is s for s in selected)
        ]
        ports["selected"] = ", ".join(indices)
    return ports


# ----------------------------------------------------------------- labels ---


def _comparison(expression: Any) -> str:
    return _binary(expression.operator, expression.variable, _value(expression))


def _joined(leaf: Any) -> str:
    # One pair of brackets around the whole check keeps "not (a xor b)" and
    # "C and (a xor b)" unambiguous; comparisons bind tighter than the word.
    word = _WORDS.get(leaf.operator) or _name(leaf.operator)
    return f"({f' {word} '.join(_comparison(check) for check in leaf.checks)})"


def _binary(op: Any, left: str, right: str) -> str:
    symbol = _SYMBOLS.get(op)
    return f"{left} {symbol} {right}" if symbol else f"{_name(op)}({left}, {right})"


def _value(expression: Any) -> str:
    generator = getattr(expression, "value_generator", None)
    if generator is None:  # py_trees < 2.4 stores the value itself
        return _literal(expression.value)
    closure = getattr(generator, "__closure__", None)
    if generator.__qualname__.startswith("ComparisonExpression.") and closure:
        # A constant, wrapped as `lambda: value`: read it, do not call it.
        return _literal(closure[0].cell_contents)
    return f"{_name(generator)}()"


def _literal(value: object) -> str:
    if isinstance(value, enum.Enum):
        return value.name
    if type(value).__module__ == "builtins":
        return repr(value)
    return f"<{type(value).__name__}>"


def _name(function: object) -> str:
    return str(getattr(function, "__name__", type(function).__name__))
