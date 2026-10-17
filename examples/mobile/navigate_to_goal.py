"""Mobile: drive to a goal, or dock first when the battery is low, in py_trees.

The same mission as navigate_to_goal.xml, with one difference: py_trees has no
IfThenElse. The usual way to write "charge or navigate" is a Selector over
[Sequence(IsBatteryLow, dock), navigate], and there a failed dock falls through
to navigation. Beehave shows it as three edges the XML version does not have::

    beehave graph --py-trees examples/mobile/navigate_to_goal.py:create_root \
        -c examples/beehave.yaml

The behaviours are stand-ins that always succeed; only the shape of the tree
matters here.
"""

from __future__ import annotations

import py_trees
from py_trees.common import Status
from py_trees.composites import Selector, Sequence


class Action(py_trees.behaviour.Behaviour):
    """A stand-in for real work, named after its class unless told otherwise."""

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name or type(self).__name__)

    def update(self) -> Status:
        """Succeed at once."""
        return Status.SUCCESS


class Check(Action):
    """A stand-in for a condition; examples/beehave.yaml says so."""


class IsBatteryLow(Check):
    """Does the robot need to charge first?"""


class IsStuck(Check):
    """Is the robot unable to move?"""


class ComputePathToPose(Action):
    """Plan a path to a pose."""


class FollowPath(Action):
    """Drive along the path."""


class DockRobot(Action):
    """Dock on the charger."""


class BackUp(Action):
    """Reverse a little."""


class ClearCostmaps(Action):
    """Forget obstacles that may be stale."""


class Spin(Action):
    """Turn on the spot to look around."""


class Wait(Action):
    """Wait a moment."""


def dock() -> py_trees.behaviour.Behaviour:
    """Plan to the dock, drive there and dock."""
    return Sequence(
        "Dock",
        memory=True,
        children=[ComputePathToPose("PlanToDock"), FollowPath("FollowDockPath"), DockRobot()],
    )


def recovery() -> py_trees.behaviour.Behaviour:
    """Try to get unstuck, then to clear the view, then wait."""
    unstick = Sequence("unstick", memory=True, children=[IsStuck(), BackUp()])
    reset_view = Sequence("reset_view", memory=True, children=[ClearCostmaps(), Spin()])
    return Selector("Recovery", memory=True, children=[unstick, reset_view, Wait()])


def create_root() -> py_trees.behaviour.Behaviour:
    """Charge when the battery is low, otherwise navigate with recovery."""
    recover_and_retry = Sequence(
        "recover_and_retry",
        memory=True,
        children=[recovery(), ComputePathToPose("Replan"), FollowPath("FollowNewPath")],
    )
    navigate = Sequence(
        "navigate",
        memory=True,
        children=[
            ComputePathToPose(),
            Selector("follow_or_recover", memory=True, children=[FollowPath(), recover_and_retry]),
        ],
    )
    charge = Sequence("charge", memory=True, children=[IsBatteryLow(), dock()])
    return Selector("NavigateToGoal", memory=True, children=[charge, navigate])
