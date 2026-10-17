"""The three examples in examples/, one per kind of robot.

The expected graphs below were derived by hand from the trees, so these tests
check the walk on realistic trees, not just on itself.
"""

from __future__ import annotations

import pytest

import beehave
from tests.conftest import EXAMPLES

AERIAL = EXAMPLES / "aerial" / "drone_mission.xml"
MOBILE = EXAMPLES / "mobile" / "navigate_to_goal.xml"
MANIPULATION = EXAMPLES / "manipulation" / "pick_and_place.xml"


def test_drone_mission() -> None:
    result = beehave.analyze(AERIAL)

    assert beehave.to_text(result.graph) == (
        "START --[IsBatteryCritical]--> LandNow\n"
        "START --[not IsBatteryCritical]--> Arm\n"
        "LandNow --[success]--> SUCCESS\n"
        "LandNow --[failure]--> Arm\n"
        "Arm --[success]--> TakeOff\n"
        "Arm --[failure]--> FAILURE\n"
        "TakeOff --[success and IsBatteryOK]--> FlyToWaypoint\n"
        "TakeOff --[success and not IsBatteryOK]--> FlyHome\n"
        "TakeOff --[failure]--> FAILURE\n"
        "FlyToWaypoint --[success]--> CaptureImage\n"
        "FlyToWaypoint --[failure]--> FlyHome\n"
        "CaptureImage --[success]--> FlyHome\n"
        "CaptureImage --[failure]--> FlyHome\n"
        "FlyHome --[success]--> Land\n"
        "FlyHome --[failure]--> FindLandingSpot\n"
        "FindLandingSpot --[success]--> FlyToLandingSpot\n"
        "FindLandingSpot --[failure]--> FAILURE\n"
        "FlyToLandingSpot --[success]--> Land\n"
        "FlyToLandingSpot --[failure]--> FAILURE\n"
        "Land --[success]--> Disarm\n"
        "Land --[failure]--> FAILURE\n"
        "Disarm --[success]--> SUCCESS\n"
        "Disarm --[failure]--> FAILURE\n"
        "\n"
        "notes:\n"
        "  FlyToWaypoint: retry ×3\n"
    )
    stats = result.stats
    assert (stats.nodes, stats.actions, stats.transitions) == (22, 10, 23)
    assert stats.approximated == {
        "ReactiveFallback": 1,
        "ReactiveSequence": 1,
        "RetryUntilSuccessful": 1,
    }


def test_mobile_navigation_is_modelled_exactly() -> None:
    result = beehave.analyze(MOBILE)

    assert beehave.to_text(result.graph) == (
        "START --[IsBatteryLow]--> PlanToDock\n"
        "START --[not IsBatteryLow]--> ComputePathToPose\n"
        "PlanToDock --[success]--> FollowDockPath\n"
        "PlanToDock --[failure]--> FAILURE\n"
        "FollowDockPath --[success]--> DockRobot\n"
        "FollowDockPath --[failure]--> FAILURE\n"
        "DockRobot --[success]--> SUCCESS\n"
        "DockRobot --[failure]--> FAILURE\n"
        "ComputePathToPose --[success]--> FollowPath\n"
        "ComputePathToPose --[failure]--> FAILURE\n"
        "FollowPath --[success]--> SUCCESS\n"
        "FollowPath --[failure and IsStuck]--> BackUp\n"
        "FollowPath --[failure and not IsStuck]--> ClearCostmaps\n"
        "BackUp --[success]--> Replan\n"
        "BackUp --[failure]--> ClearCostmaps\n"
        "ClearCostmaps --[success]--> Spin\n"
        "ClearCostmaps --[failure]--> Wait\n"
        "Spin --[success]--> Replan\n"
        "Spin --[failure]--> Wait\n"
        "Wait --[success]--> Replan\n"
        "Wait --[failure]--> FAILURE\n"
        "Replan --[success]--> FollowNewPath\n"
        "Replan --[failure]--> FAILURE\n"
        "FollowNewPath --[success]--> SUCCESS\n"
        "FollowNewPath --[failure]--> FAILURE\n"
    )
    stats = result.stats
    assert (stats.nodes, stats.actions, stats.transitions) == (23, 11, 25)
    assert result.graph.diagnostics == ()


def test_pick_and_place() -> None:
    result = beehave.analyze(MANIPULATION)

    assert beehave.to_text(result.graph) == (
        "START --> DetectObject\n"
        "DetectObject --[success and IsObjectReachable]--> PlanGrasp\n"
        "DetectObject --[success and not IsObjectReachable]--> SafeRelease\n"
        "DetectObject --[failure]--> SafeRelease\n"
        "PlanGrasp --[success]--> MoveToPregrasp\n"
        "PlanGrasp --[failure]--> SafeRelease\n"
        "MoveToPregrasp --[success]--> OpenGripper\n"
        "MoveToPregrasp --[failure]--> SafeRelease\n"
        "OpenGripper --[success]--> ApproachObject\n"
        "OpenGripper --[failure]--> SafeRelease\n"
        "ApproachObject --[success]--> CloseGripper\n"
        "ApproachObject --[failure]--> SafeRelease\n"
        "CloseGripper --[success and IsObjectGrasped]--> LiftObject\n"
        "CloseGripper --[success and not IsObjectGrasped]--> SafeRelease\n"
        "CloseGripper --[failure]--> SafeRelease\n"
        "LiftObject --[success]--> MoveToPlace\n"
        "LiftObject --[failure]--> SafeRelease\n"
        "SafeRelease --[success]--> AbortToHome\n"
        "SafeRelease --[failure]--> FAILURE\n"
        "AbortToHome --[success]--> FAILURE\n"
        "AbortToHome --[failure]--> FAILURE\n"
        "MoveToPlace --[success]--> Release\n"
        "MoveToPlace --[failure]--> FAILURE\n"
        "Release --[success]--> Retreat\n"
        "Release --[failure]--> FAILURE\n"
        "Retreat --[success]--> MoveToHome\n"
        "Retreat --[failure]--> FAILURE\n"
        "MoveToHome --[success]--> SUCCESS\n"
        "MoveToHome --[failure]--> FAILURE\n"
        "\n"
        "notes:\n"
        "  PlanGrasp: retry ×3\n"
    )
    stats = result.stats
    assert (stats.nodes, stats.actions, stats.transitions) == (24, 13, 29)
    assert stats.approximated == {"RetryUntilSuccessful": 1}


@pytest.mark.parametrize("example", [AERIAL, MOBILE, MANIPULATION], ids=lambda p: p.stem)
def test_examples_render_in_every_format(example: object) -> None:
    graph = beehave.analyze(example).graph  # type: ignore[arg-type]

    for render in (beehave.to_text, beehave.to_mermaid, beehave.to_dot, beehave.to_json):
        assert render(graph)
