"""Manipulation: pick an object and place it, in py_trees.

The same tree as pick_and_place.xml, built the way a py_trees project builds a
tree: a function returns its root. Beehave reads the tree without ticking it::

    beehave graph --py-trees examples/manipulation/pick_and_place.py:create_root \
        -c examples/beehave.yaml

The behaviours are stand-ins that always succeed; only the shape of the tree
matters here.
"""

from __future__ import annotations

import py_trees
from py_trees.common import Status
from py_trees.composites import Selector, Sequence
from py_trees.decorators import Retry


class Action(py_trees.behaviour.Behaviour):
    """A stand-in for real work, named after its class unless told otherwise."""

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name or type(self).__name__)

    def update(self) -> Status:
        """Succeed at once."""
        return Status.SUCCESS


class Check(Action):
    """A stand-in for a condition; examples/beehave.yaml says so."""


class IsObjectReachable(Check):
    """Can the arm reach the object?"""


class IsObjectGrasped(Check):
    """Is the object in the gripper?"""


class DetectObject(Action):
    """Find the object and its pose."""


class PlanGrasp(Action):
    """Plan how to grasp it."""


class MoveToPregrasp(Action):
    """Move the arm next to the object."""


class OpenGripper(Action):
    """Open the gripper."""


class ApproachObject(Action):
    """Move in to the grasp pose."""


class CloseGripper(Action):
    """Close the gripper."""


class LiftObject(Action):
    """Lift the object."""


class MoveToHome(Action):
    """Move the arm to its rest pose."""


class MoveToPlace(Action):
    """Move the object to where it goes."""


class Retreat(Action):
    """Move the arm away from the object."""


def pick() -> py_trees.behaviour.Behaviour:
    """Pick the object, or release whatever is held and give up."""
    attempt = Sequence(
        "pick",
        memory=True,
        children=[
            DetectObject(),
            IsObjectReachable(),
            Retry("retry", PlanGrasp(), num_failures=3),
            MoveToPregrasp(),
            OpenGripper(),
            ApproachObject(),
            CloseGripper(),
            IsObjectGrasped(),
            LiftObject(),
        ],
    )
    give_up = Sequence(
        "give_up",
        memory=True,
        children=[
            OpenGripper("SafeRelease"),
            MoveToHome("AbortToHome"),
            py_trees.behaviours.Failure("Fail"),
        ],
    )
    return Selector("pick_or_give_up", memory=True, children=[attempt, give_up])


def place() -> py_trees.behaviour.Behaviour:
    """Place the object, release it and move back home."""
    return Sequence(
        "Place",
        memory=True,
        children=[MoveToPlace(), OpenGripper("Release"), Retreat(), MoveToHome()],
    )


def create_root() -> py_trees.behaviour.Behaviour:
    """Pick, then place."""
    return Sequence("PickAndPlace", memory=True, children=[pick(), place()])
