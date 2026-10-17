"""The py_trees adapter: a live py_trees tree becomes the shared model."""

from __future__ import annotations

import functools
import operator
import sys
import types
from typing import TYPE_CHECKING, Any

import pytest

from beehave.config import Config
from beehave.errors import BeehaveError, ParseError, UnsupportedFormatError
from beehave.model import Node, NodeKind, Semantics

pytest.importorskip("py_trees")

import py_trees
from py_trees import behaviours, composites, decorators
from py_trees.common import (
    ComparisonExpression,
    OneShotPolicy,
    ParallelPolicy,
    Status,
)

from beehave.parsers.pytrees import from_py_trees

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator


# ForEach, CompareBlackboardVariables and callable comparison values.
SINCE_2_4 = pytest.mark.skipif(not hasattr(decorators, "ForEach"), reason="added in py_trees 2.4")


@pytest.fixture(autouse=True)
def _clean_blackboard() -> Iterator[None]:
    # Behaviours register blackboard clients in a process-wide registry.
    yield
    py_trees.blackboard.Blackboard.clear()


class Arm(py_trees.behaviour.Behaviour):
    """A user action."""

    def __init__(self, name: str = "Arm") -> None:
        super().__init__(name)

    def update(self) -> Status:
        return Status.SUCCESS


class IsAt(py_trees.behaviour.Behaviour):
    """A user condition with a constructor argument Beehave cannot see."""

    def __init__(self, name: str, place: str) -> None:
        super().__init__(name)
        self.place = place

    def update(self) -> Status:
        return Status.SUCCESS


def root_of(tree: object, config: Config | None = None) -> Node:
    document = from_py_trees(tree, config=config)
    assert document.main_tree is not None
    return document.trees[document.main_tree].root


def only_child(tree: object) -> Node:
    return root_of(tree).children[0]


def expression(check: py_trees.behaviour.Behaviour) -> str:
    node = only_child(composites.Sequence("root", memory=True, children=[check]))
    assert node.kind is NodeKind.CONDITION
    assert node.semantics is Semantics.BLACKBOARD_CONDITION
    return node.ports["expression"]


# ---------------------------------------------------------------- document ---


def test_document_holds_one_tree_named_after_the_root() -> None:
    document = from_py_trees(composites.Sequence("Mission", memory=True, children=[Arm()]))

    assert document.format == "py_trees"
    assert list(document.trees) == ["Mission"]
    assert document.main_tree == "Mission"
    assert document.diagnostics == ()


def test_a_behaviour_tree_is_unwrapped() -> None:
    tree = py_trees.trees.BehaviourTree(composites.Sequence("Mission", memory=True))

    assert root_of(tree).type == "Sequence(memory=True)"


def test_anything_else_is_refused() -> None:
    with pytest.raises(BeehaveError, match="expected a py_trees Behaviour or BehaviourTree"):
        from_py_trees("Mission")


def test_newlines_in_names_become_spaces() -> None:
    node = root_of(composites.Sequence("Mark\ntask_done", memory=True))

    assert node.name == "Mark task_done"


def test_a_node_shared_by_two_parents_is_refused() -> None:
    shared = Arm()
    first = composites.Sequence("first", memory=True, children=[shared])
    second = composites.Sequence("second", memory=True)
    second.insert_child(shared, 0)  # insert_child does not check for a parent

    with pytest.raises(ParseError, match="'Arm' appears twice in the tree"):
        from_py_trees(composites.Sequence("root", memory=True, children=[first, second]))


def test_a_cycle_is_refused() -> None:
    root = composites.Sequence("root", memory=True)
    root.insert_child(root, 0)

    with pytest.raises(ParseError, match="'root' appears twice in the tree"):
        from_py_trees(root)


def test_a_missing_py_trees_names_the_fix(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "py_trees", None)

    with pytest.raises(UnsupportedFormatError, match=r"pip install 'beehave-bt\[py-trees\]'"):
        from_py_trees(object())


def test_an_old_py_trees_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(py_trees.version, "__version__", "2.1.6")

    with pytest.raises(UnsupportedFormatError, match=r"needs py_trees >= 2\.2, found 2\.1\.6"):
        from_py_trees(Arm())


# -------------------------------------------------------------- composites ---


@pytest.mark.parametrize(
    ("composite", "semantics", "type_"),
    [
        (composites.Sequence("s", memory=True), Semantics.SEQUENCE, "Sequence(memory=True)"),
        (
            composites.Sequence("s", memory=False),
            Semantics.REACTIVE_SEQUENCE,
            "Sequence(memory=False)",
        ),
        (composites.Selector("s", memory=True), Semantics.FALLBACK, "Selector(memory=True)"),
        (
            composites.Selector("s", memory=False),
            Semantics.REACTIVE_FALLBACK,
            "Selector(memory=False)",
        ),
    ],
    ids=["sequence", "reactive-sequence", "selector", "reactive-selector"],
)
def test_memory_decides_between_plain_and_reactive(
    composite: py_trees.composites.Composite, semantics: Semantics, type_: str
) -> None:
    # py_trees "memory" only resumes a RUNNING child; after SUCCESS or FAILURE
    # the next activation restarts at the first child, like BT.CPP's Sequence.
    node = root_of(composite)

    assert (node.kind, node.semantics, node.type, node.name) == (
        NodeKind.CONTROL,
        semantics,
        type_,
        "s",
    )


@pytest.mark.parametrize(
    ("policy", "ports"),
    [
        (ParallelPolicy.SuccessOnAll(), {"policy": "SuccessOnAll", "synchronise": "true"}),
        (
            ParallelPolicy.SuccessOnAll(synchronise=False),
            {"policy": "SuccessOnAll", "synchronise": "false"},
        ),
        (ParallelPolicy.SuccessOnOne(), {"policy": "SuccessOnOne", "synchronise": "false"}),
    ],
    ids=["all", "all-unsynchronised", "one"],
)
def test_parallel_records_its_policy(
    policy: py_trees.common.ParallelPolicy.Base, ports: dict[str, str]
) -> None:
    node = root_of(composites.Parallel("p", policy=policy, children=[Arm(), Arm("Disarm")]))

    assert (node.semantics, node.type, dict(node.ports)) == (Semantics.PARALLEL, "Parallel", ports)


def test_parallel_success_on_selected_records_child_indices() -> None:
    a, b, c = Arm("a"), Arm("b"), Arm("c")
    policy = ParallelPolicy.SuccessOnSelected([c, a])

    node = root_of(composites.Parallel("p", policy=policy, children=[a, b, c]))

    assert node.ports["policy"] == "SuccessOnSelected"
    assert node.ports["selected"] == "0, 2"


def test_children_keep_their_order() -> None:
    node = root_of(composites.Selector("s", memory=True, children=[Arm("a"), Arm("b")]))

    assert [c.name for c in node.children] == ["a", "b"]


def test_user_composite_with_its_own_tick_is_custom() -> None:
    class Shuffle(composites.Composite):
        def tick(self) -> Iterator[py_trees.behaviour.Behaviour]:
            yield self

    node = root_of(Shuffle("shuffle", children=[Arm()]))

    assert (node.kind, node.semantics, node.type) == (NodeKind.CONTROL, Semantics.CUSTOM, "Shuffle")


def test_user_subclass_without_tick_logic_keeps_the_builtin_semantics() -> None:
    class Guarded(composites.Sequence):
        def __init__(self, name: str) -> None:
            super().__init__(name, memory=False)

    node = root_of(Guarded("guarded"))

    assert (node.semantics, node.type) == (Semantics.REACTIVE_SEQUENCE, "Guarded(memory=False)")


# -------------------------------------------------------------- decorators ---


def _decorate(make: type[py_trees.decorators.Decorator], **kwargs: object) -> Node:
    return root_of(make(name="d", child=Arm(), **kwargs))


@pytest.mark.parametrize(
    ("decorator", "kwargs", "semantics", "ports"),
    [
        (decorators.Inverter, {}, Semantics.INVERTER, {}),
        (decorators.SuccessIsFailure, {}, Semantics.FORCE_FAILURE, {}),
        (decorators.FailureIsSuccess, {}, Semantics.FORCE_SUCCESS, {}),
        (decorators.SuccessIsRunning, {}, Semantics.KEEP_RUNNING_UNTIL_FAILURE, {}),
        (decorators.FailureIsRunning, {}, Semantics.RETRY, {}),
        (decorators.Retry, {"num_failures": 3}, Semantics.RETRY, {"num_failures": "3"}),
        (decorators.Repeat, {"num_success": 2}, Semantics.REPEAT, {"num_success": "2"}),
        (decorators.Timeout, {"duration": 1.5}, Semantics.TIMEOUT, {"duration": "1.5"}),
        (
            decorators.OneShot,
            {"policy": OneShotPolicy.ON_COMPLETION},
            Semantics.RUN_ONCE,
            {"policy": "ON_COMPLETION"},
        ),
        (decorators.PassThrough, {}, Semantics.PASS_THROUGH, {}),
        (decorators.Count, {}, Semantics.PASS_THROUGH, {}),
        (
            decorators.StatusToBlackboard,
            {"variable_name": "result"},
            Semantics.PASS_THROUGH,
            {"variable_name": "result"},
        ),
    ],
    ids=lambda v: v.__name__ if isinstance(v, type) else None,
)
def test_decorators(
    decorator: type[py_trees.decorators.Decorator],
    kwargs: dict[str, object],
    semantics: Semantics,
    ports: dict[str, str],
) -> None:
    node = _decorate(decorator, **kwargs)

    assert (node.kind, node.semantics, node.type, dict(node.ports)) == (
        NodeKind.DECORATOR,
        semantics,
        decorator.__name__,
        ports,
    )
    assert [c.name for c in node.children] == ["Arm"]


@pytest.mark.parametrize(
    ("decorator", "kwargs", "ports"),
    [
        (
            decorators.RunningIsFailure,
            {},
            {"on_success": "SUCCESS", "on_failure": "FAILURE", "on_running": "FAILURE"},
        ),
        (
            decorators.RunningIsSuccess,
            {},
            {"on_success": "SUCCESS", "on_failure": "FAILURE", "on_running": "SUCCESS"},
        ),
        (
            decorators.Condition,
            {"status": Status.FAILURE},
            {"on_success": "RUNNING", "on_failure": "SUCCESS", "on_running": "RUNNING"},
        ),
        (
            decorators.Condition,
            {"status": Status.RUNNING},
            {"on_success": "RUNNING", "on_failure": "RUNNING", "on_running": "SUCCESS"},
        ),
    ],
    ids=["running-is-failure", "running-is-success", "until-failure", "until-running"],
)
def test_status_maps(
    decorator: type[py_trees.decorators.Decorator],
    kwargs: dict[str, object],
    ports: dict[str, str],
) -> None:
    node = _decorate(decorator, **kwargs)

    assert (node.semantics, dict(node.ports)) == (Semantics.STATUS_MAP, ports)


def test_condition_waiting_for_success_is_an_unbounded_retry() -> None:
    # Condition(SUCCESS) maps S->S, F->RUNNING, R->RUNNING: FailureIsRunning.
    node = _decorate(decorators.Condition, status=Status.SUCCESS)

    assert (node.semantics, dict(node.ports)) == (Semantics.RETRY, {})


@SINCE_2_4
def test_for_each_repeats_once_per_item() -> None:
    node = _decorate(decorators.ForEach, source_key="waypoints", target_key="waypoint")

    assert node.semantics is Semantics.REPEAT
    assert dict(node.ports) == {"source_key": "waypoints", "target_key": "waypoint"}


def test_eternal_guard_becomes_a_reactive_sequence_over_its_condition() -> None:
    def battery_ok() -> bool:
        return True

    node = root_of(decorators.EternalGuard("Battery OK?", Arm(), condition=battery_ok))

    assert (node.kind, node.semantics, node.type, node.name) == (
        NodeKind.CONTROL,
        Semantics.REACTIVE_SEQUENCE,
        "EternalGuard",
        "Battery OK?",
    )
    guard, child = node.children
    assert (guard.kind, guard.semantics, guard.type, guard.name) == (
        NodeKind.CONDITION,
        Semantics.CUSTOM,
        "battery_ok",
        "Battery OK?",
    )
    assert child.name == "Arm"


def test_eternal_guard_with_a_blackboard_condition_names_the_function() -> None:
    def low(blackboard: object) -> bool:
        return bool(blackboard)

    guard = decorators.EternalGuard(
        "Battery Low?", Arm(), condition=low, blackboard_keys={"battery_low", "armed"}
    )
    assert isinstance(guard.condition, functools.partial)

    condition = root_of(guard).children[0]

    assert condition.type == "low"
    assert dict(condition.ports) == {"blackboard_keys": "armed, battery_low"}


def test_user_decorator_with_its_own_update_is_custom() -> None:
    class Throttle(decorators.Decorator):
        def update(self) -> Status:
            return self.decorated.status

    node = root_of(Throttle("throttle", Arm()))

    assert (node.kind, node.semantics, node.type) == (
        NodeKind.DECORATOR,
        Semantics.CUSTOM,
        "Throttle",
    )


# ------------------------------------------------------------------ leaves ---


@pytest.mark.parametrize(
    ("leaf", "kind", "semantics"),
    [
        (behaviours.Success("Success"), NodeKind.ACTION, Semantics.ALWAYS_SUCCESS),
        (behaviours.Failure("Failure"), NodeKind.ACTION, Semantics.ALWAYS_FAILURE),
        (behaviours.Running("Idle"), NodeKind.ACTION, Semantics.ALWAYS_RUNNING),
        (behaviours.Dummy("Dummy"), NodeKind.ACTION, Semantics.ALWAYS_RUNNING),
        (py_trees.timers.Timer("Wait", duration=2.0), NodeKind.ACTION, Semantics.WAIT),
        (
            behaviours.SetBlackboardVariable("Mark", "done", True, overwrite=True),
            NodeKind.ACTION,
            Semantics.SET_BLACKBOARD,
        ),
        (
            behaviours.UnsetBlackboardVariable("Clear", "done"),
            NodeKind.ACTION,
            Semantics.SET_BLACKBOARD,
        ),
        (
            behaviours.SetBlackboardVariable("Claim", "owner", "me", overwrite=False),
            NodeKind.ACTION,
            Semantics.CUSTOM,
        ),
        (behaviours.SuccessEveryN("Every 3", 3), NodeKind.CONDITION, Semantics.CUSTOM),
        (behaviours.BlackboardToStatus("Result", "result"), NodeKind.CONDITION, Semantics.CUSTOM),
        (behaviours.TickCounter("Work", 3, Status.SUCCESS), NodeKind.ACTION, Semantics.CUSTOM),
        (behaviours.Periodic("Flip", 2), NodeKind.ACTION, Semantics.CUSTOM),
        (
            behaviours.StatusQueue("Script", [Status.SUCCESS], eventually=None),
            NodeKind.ACTION,
            Semantics.CUSTOM,
        ),
    ],
    ids=lambda v: getattr(v, "name", None),
)
def test_builtin_leaves(
    leaf: py_trees.behaviour.Behaviour, kind: NodeKind, semantics: Semantics
) -> None:
    node = only_child(composites.Sequence("root", memory=True, children=[leaf]))

    assert (node.kind, node.semantics, node.type) == (kind, semantics, type(leaf).__name__)


def test_timer_records_its_duration() -> None:
    node = only_child(
        composites.Sequence("root", memory=True, children=[py_trees.timers.Timer(duration=2.0)])
    )

    assert (node.name, dict(node.ports)) == ("Timer", {"duration": "2.0"})


def test_blackboard_to_status_is_reported() -> None:
    document = from_py_trees(behaviours.BlackboardToStatus("Result", "result"))

    (diagnostic,) = document.diagnostics
    assert diagnostic.code == "approximated"
    assert "returns the status stored in result" in diagnostic.message


def test_user_leaves_are_actions_by_default() -> None:
    node = only_child(composites.Sequence("root", memory=True, children=[Arm()]))

    assert (node.kind, node.semantics, node.type, node.name) == (
        NodeKind.ACTION,
        Semantics.CUSTOM,
        "Arm",
        "Arm",
    )


@pytest.mark.parametrize("listed", ["IsAt", f"{__name__}.IsAt"])
def test_config_names_user_conditions_by_class(listed: str) -> None:
    config = Config(conditions=frozenset({listed}))
    tree = composites.Sequence("root", memory=True, children=[IsAt("At dock?", "dock")])

    node = root_of(tree, config).children[0]

    assert (node.kind, node.type, node.name) == (NodeKind.CONDITION, "IsAt", "At dock?")


def test_config_can_name_a_base_class() -> None:
    class Check(py_trees.behaviour.Behaviour):
        def update(self) -> Status:
            return Status.SUCCESS

    class IsDocked(Check):
        pass

    class IsCharging(Check):
        pass

    config = Config(conditions=frozenset({"Check"}), actions=frozenset({"IsCharging"}))
    tree = composites.Sequence("root", memory=True, children=[IsDocked("d"), IsCharging("c")])

    kinds = [c.kind for c in root_of(tree, config).children]

    # The nearest class in the MRO that the config names decides.
    assert kinds == [NodeKind.CONDITION, NodeKind.ACTION]


def test_config_can_turn_a_stand_in_into_a_condition() -> None:
    queue = behaviours.StatusQueue("Condition 1", [Status.SUCCESS], eventually=None)
    config = Config(conditions=frozenset({"StatusQueue"}))

    node = root_of(composites.Sequence("root", memory=True, children=[queue]), config)

    assert node.children[0].kind is NodeKind.CONDITION


def test_config_can_turn_a_builtin_condition_into_an_action() -> None:
    config = Config(actions=frozenset({"SuccessEveryN"}))
    tree = composites.Sequence("root", memory=True, children=[behaviours.SuccessEveryN("n", 2)])

    assert root_of(tree, config).children[0].kind is NodeKind.ACTION


def test_wait_for_is_not_taken_for_the_check_it_subclasses() -> None:
    check = ComparisonExpression("battery_level", 20, operator.lt)
    wait = behaviours.WaitForBlackboardVariableValue("Wait for charge", check)
    assert isinstance(wait, behaviours.CheckBlackboardVariableValue)

    node = only_child(composites.Sequence("root", memory=True, children=[wait]))

    assert (node.kind, node.semantics, dict(node.ports)) == (
        NodeKind.ACTION,
        Semantics.WAIT,
        {"expression": "battery_level < 20"},
    )


def test_wait_for_a_variable_is_a_wait() -> None:
    wait = behaviours.WaitForBlackboardVariable("Wait for goal", "goal")

    node = only_child(composites.Sequence("root", memory=True, children=[wait]))

    assert (node.semantics, dict(node.ports)) == (Semantics.WAIT, {"expression": "goal is set"})


def test_user_subclass_of_a_check_is_still_a_check() -> None:
    class LowBattery(behaviours.CheckBlackboardVariableValue):
        pass

    check = LowBattery("Low?", ComparisonExpression("battery_level", 20, operator.lt))

    assert expression(check) == "battery_level < 20"


def test_a_leaf_with_children_is_walked_as_a_custom_control() -> None:
    leaf = Arm("bundle")
    leaf.children.append(Arm())

    node = root_of(leaf)

    assert (node.kind, node.semantics) == (NodeKind.CONTROL, Semantics.CUSTOM)


# ------------------------------------------------- blackboard check labels ---


@pytest.mark.parametrize(
    ("op", "value", "label"),
    [
        (operator.lt, 20, "battery_level < 20"),
        (operator.le, 20, "battery_level <= 20"),
        (operator.eq, "docked", "battery_level == 'docked'"),
        (operator.ne, True, "battery_level != True"),
        (operator.ge, 2.5, "battery_level >= 2.5"),
        (operator.gt, Status.SUCCESS, "battery_level > SUCCESS"),
    ],
    ids=lambda v: getattr(v, "__name__", None),
)
def test_comparison_labels(op: Callable[[Any, Any], bool], value: object, label: str) -> None:
    check = behaviours.CheckBlackboardVariableValue(
        "check", ComparisonExpression("battery_level", value, op)
    )

    assert expression(check) == label


@SINCE_2_4
def test_a_callable_value_is_named_not_called() -> None:
    called = []

    def threshold() -> float:
        called.append(True)
        return 20.0

    check = behaviours.CheckBlackboardVariableValue(
        "check", ComparisonExpression("battery_level", threshold, operator.lt)
    )

    assert expression(check) == "battery_level < threshold()"
    assert called == []


def test_an_unknown_operator_is_shown_as_a_call() -> None:
    def within(value: float, limit: float) -> bool:
        return abs(value) <= limit

    check = behaviours.CheckBlackboardVariableValue(
        "check", ComparisonExpression("drift", 0.1, within)
    )

    assert expression(check) == "within(drift, 0.1)"


def test_variable_exists() -> None:
    check = behaviours.CheckBlackboardVariableExists("Goal?", "goal")

    assert expression(check) == "goal is set"


def test_several_checks_joined_by_an_operator() -> None:
    check = behaviours.CheckBlackboardVariableValues(
        "XOR",
        checks=[
            ComparisonExpression("joy1", "enabled", operator.eq),
            ComparisonExpression("joy2", "enabled", operator.eq),
        ],
        operator=operator.xor,
    )

    assert expression(check) == "(joy1 == 'enabled' xor joy2 == 'enabled')"


@SINCE_2_4
def test_compare_two_variables() -> None:
    check = behaviours.CompareBlackboardVariables("Too fast?", "speed", "limit", operator.gt)

    assert expression(check) == "speed > limit"


def test_a_value_of_a_user_type_is_not_printed() -> None:
    class Pose:
        def __repr__(self) -> str:  # pragma: no cover - must not be called
            raise AssertionError

    check = behaviours.CheckBlackboardVariableValue(
        "check", ComparisonExpression("pose", Pose(), operator.eq)
    )

    assert expression(check) == "pose == <Pose>"


def test_py_trees_before_2_4_stores_the_value_itself() -> None:
    check = behaviours.CheckBlackboardVariableValue(
        "check", ComparisonExpression("battery_level", 20, operator.lt)
    )
    old_style: Any = types.SimpleNamespace(variable="battery_level", operator=operator.lt, value=20)
    check.check = old_style

    assert expression(check) == "battery_level < 20"
