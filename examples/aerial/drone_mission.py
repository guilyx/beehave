"""Aerial: a multirotor survey mission, in py_trees.

The same tree as drone_mission.xml, built the way a py_trees project builds a
tree: a function returns its root. Beehave reads the tree without ticking it::

    beehave graph --py-trees examples/aerial/drone_mission.py:create_root \
        -c examples/beehave.yaml

The behaviours are stand-ins that always succeed; only the shape of the tree
matters here.
"""

from __future__ import annotations

import py_trees
from py_trees.common import Status
from py_trees.composites import Selector, Sequence
from py_trees.decorators import FailureIsSuccess, Retry


class Action(py_trees.behaviour.Behaviour):
    """A stand-in for real work, named after its class unless told otherwise."""

    def __init__(self, name: str | None = None) -> None:
        super().__init__(name or type(self).__name__)

    def update(self) -> Status:
        """Succeed at once."""
        return Status.SUCCESS


class Check(Action):
    """A stand-in for a condition; examples/beehave.yaml says so."""


class IsBatteryCritical(Check):
    """Is the battery too low to fly on?"""


class IsBatteryOK(Check):
    """Is there enough battery for the survey?"""


class LandNow(Action):
    """Land where the drone is."""


class Arm(Action):
    """Arm the motors."""


class TakeOff(Action):
    """Climb to cruise altitude."""


class FlyToWaypoint(Action):
    """Fly to the survey point."""


class CaptureImage(Action):
    """Take the picture."""


class FlyHome(Action):
    """Return to the launch point."""


class FindLandingSpot(Action):
    """Look for somewhere else to land."""


class FlyToLandingSpot(Action):
    """Fly to that spot."""


class Land(Action):
    """Land."""


class Disarm(Action):
    """Disarm the motors."""


def return_to_launch() -> py_trees.behaviour.Behaviour:
    """Fly home, or land somewhere else, then land and disarm."""
    divert = Sequence("divert", memory=True, children=[FindLandingSpot(), FlyToLandingSpot()])
    get_home = Selector("get_home", memory=True, children=[FlyHome(), divert])
    return Sequence("ReturnToLaunch", memory=True, children=[get_home, Land(), Disarm()])


def create_root() -> py_trees.behaviour.Behaviour:
    """The mission, behind a failsafe that lands at once on a critical battery."""
    # memory=False re-checks earlier children on every tick, like BT.CPP's
    # ReactiveSequence and ReactiveFallback.
    failsafe = Sequence("failsafe", memory=False, children=[IsBatteryCritical(), LandNow()])
    survey = Sequence(
        "survey",
        memory=True,
        children=[IsBatteryOK(), Retry("retry", FlyToWaypoint(), num_failures=3), CaptureImage()],
    )
    mission = Sequence(
        "mission",
        memory=True,
        children=[
            Arm(),
            TakeOff(),
            FailureIsSuccess("survey_is_optional", survey),
            return_to_launch(),
        ],
    )
    return Selector("DroneMission", memory=False, children=[failsafe, mission])
