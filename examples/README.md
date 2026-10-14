# Examples

Three small trees, one per kind of robot. Each file is plain BehaviorTree.CPP v3
XML and declares its node kinds in `<TreeNodesModel>`, so Beehave needs no
configuration to read it. The node names follow vocabulary that is common
across autopilots, navigation stacks and motion planners, not any one product.

| Example | Robot | Tree | Graph | What it shows |
| --- | --- | ---: | ---: | --- |
| [`aerial/drone_mission.xml`](aerial/drone_mission.xml) | Multirotor | 22 nodes | 10 actions | A reactive failsafe, a retry, a subtree, and a gap |
| [`mobile/navigate_to_goal.xml`](mobile/navigate_to_goal.xml) | Mobile base | 23 nodes | 11 actions | `IfThenElse`, recovery behaviours, two subtrees; no approximation |
| [`manipulation/pick_and_place.xml`](manipulation/pick_and_place.xml) | Arm and gripper | 24 nodes | 13 actions | Two checks, a safe abort, and a missing failure path |

Try them:

```console
$ beehave graph examples/aerial/drone_mission.xml
$ beehave stats examples/mobile/navigate_to_goal.xml
$ beehave graph examples/manipulation/pick_and_place.xml -f mermaid
```

## Aerial: a drone survey mission

Arm, take off, fly to a waypoint and take a picture, then return to launch
whether or not the survey worked. A failsafe lands at once if the battery
becomes critical.

What to look for:

- `IsBatteryCritical` guards the first transition: the failsafe is checked
  before anything else.
- **A gap:** `LandNow` fails over to `Arm`. If the emergency landing fails,
  the fallback moves on to the mission and the drone would start again. The
  XML hides this; the graph shows it as one arrow.
- When `IsBatteryOK` does not hold, the drone skips the survey and flies home.
- The failsafe is reactive. Phase 1 walks it like a plain fallback and says
  so in a warning; preemption edges come in Phase 2.

```mermaid
---
config:
  theme: base
  themeVariables:
    edgeLabelBackground: "#f5f0e9"
    lineColor: "#1b1813"
---
%% Beehave action graph: DroneMission (btcpp-v3)
flowchart TD
    start(("START"))
    a1["LandNow"]
    a2["Arm"]
    a3["TakeOff"]
    a4["FlyToWaypoint<br/><small>retry ×3</small>"]
    a5["CaptureImage"]
    a6["FlyHome"]
    a7["FindLandingSpot"]
    a8["FlyToLandingSpot"]
    a9["Land"]
    a10["Disarm"]
    success(["SUCCESS"])
    failure(["FAILURE"])
    start -->|"IsBatteryCritical"| a1
    start -->|"not IsBatteryCritical"| a2
    a1 -->|"success"| success
    a1 -.->|"failure"| a2
    a2 -->|"success"| a3
    a2 -.->|"failure"| failure
    a3 -->|"success and IsBatteryOK"| a4
    a3 -->|"success and not IsBatteryOK"| a6
    a3 -.->|"failure"| failure
    a4 -->|"success"| a5
    a4 -.->|"failure"| a6
    a5 -->|"success"| a6
    a5 -.->|"failure"| a6
    a6 -->|"success"| a9
    a6 -.->|"failure"| a7
    a7 -->|"success"| a8
    a7 -.->|"failure"| failure
    a8 -->|"success"| a9
    a8 -.->|"failure"| failure
    a9 -->|"success"| a10
    a9 -.->|"failure"| failure
    a10 -->|"success"| success
    a10 -.->|"failure"| failure
    classDef start fill:#1b1813,stroke:#1b1813,stroke-width:1.5px,color:#f5f0e9
    classDef action fill:#fdfbf9,stroke:#1b1813,stroke-width:1.5px,color:#1b1813
    classDef success fill:#107550,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    classDef failure fill:#b93917,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    class start start
    class a1,a2,a3,a4,a5,a6,a7,a8,a9,a10 action
    class success success
    class failure failure
    linkStyle 0,1 stroke:#1b1813,stroke-width:1.75px
    linkStyle 2,4,6,7,9,11,13,15,17,19,21 stroke:#107550,stroke-width:1.75px
    linkStyle 3,5,8,10,12,14,16,18,20,22 stroke:#b93917,stroke-width:1.75px,stroke-dasharray:7 4
```

## Mobile robot: navigate to a goal

If the battery is low, dock. Otherwise plan a path and follow it. If following
fails, recover (back up when stuck, else clear the costmaps and spin, else
wait), then plan again.

What to look for:

- `IsBatteryLow` splits the very first step between docking and navigating.
- The choice of recovery becomes guards on the failure edge of `FollowPath`.
- Every recovery ends in `Replan`.
- No warnings: every node in this tree is modelled exactly.

```mermaid
---
config:
  theme: base
  themeVariables:
    edgeLabelBackground: "#f5f0e9"
    lineColor: "#1b1813"
---
%% Beehave action graph: NavigateToGoal (btcpp-v3)
flowchart TD
    start(("START"))
    a1["PlanToDock"]
    a2["FollowDockPath"]
    a3["DockRobot"]
    a4["ComputePathToPose"]
    a5["FollowPath"]
    a6["BackUp"]
    a7["ClearCostmaps"]
    a8["Spin"]
    a9["Wait"]
    a10["Replan"]
    a11["FollowNewPath"]
    success(["SUCCESS"])
    failure(["FAILURE"])
    start -->|"IsBatteryLow"| a1
    start -->|"not IsBatteryLow"| a4
    a1 -->|"success"| a2
    a1 -.->|"failure"| failure
    a2 -->|"success"| a3
    a2 -.->|"failure"| failure
    a3 -->|"success"| success
    a3 -.->|"failure"| failure
    a4 -->|"success"| a5
    a4 -.->|"failure"| failure
    a5 -->|"success"| success
    a5 -.->|"failure and IsStuck"| a6
    a5 -.->|"failure and not IsStuck"| a7
    a6 -->|"success"| a10
    a6 -.->|"failure"| a7
    a7 -->|"success"| a8
    a7 -.->|"failure"| a9
    a8 -->|"success"| a10
    a8 -.->|"failure"| a9
    a9 -->|"success"| a10
    a9 -.->|"failure"| failure
    a10 -->|"success"| a11
    a10 -.->|"failure"| failure
    a11 -->|"success"| success
    a11 -.->|"failure"| failure
    classDef start fill:#1b1813,stroke:#1b1813,stroke-width:1.5px,color:#f5f0e9
    classDef action fill:#fdfbf9,stroke:#1b1813,stroke-width:1.5px,color:#1b1813
    classDef success fill:#107550,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    classDef failure fill:#b93917,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    class start start
    class a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11 action
    class success success
    class failure failure
    linkStyle 0,1 stroke:#1b1813,stroke-width:1.75px
    linkStyle 2,4,6,8,10,13,15,17,19,21,23 stroke:#107550,stroke-width:1.75px
    linkStyle 3,5,7,9,11,12,14,16,18,20,22,24 stroke:#b93917,stroke-width:1.75px,stroke-dasharray:7 4
```

## Manipulator: pick and place

Detect the object, check it is reachable, plan a grasp (up to three tries),
approach, close the gripper and check the grasp before lifting. Then move to
the place pose, release and retreat.

What to look for:

- Two checks become guards: `IsObjectReachable` after detection and
  `IsObjectGrasped` after closing the gripper.
- Every failure during the pick funnels into `SafeRelease`, then
  `AbortToHome`, then `FAILURE`. The `AlwaysFailure` leaf that forces this is
  not drawn as a box.
- **A gap:** `MoveToPlace` fails straight to `FAILURE`, with the object still
  in the gripper. The pick has a safe abort; the place does not.

```mermaid
---
config:
  theme: base
  themeVariables:
    edgeLabelBackground: "#f5f0e9"
    lineColor: "#1b1813"
---
%% Beehave action graph: PickAndPlace (btcpp-v3)
flowchart TD
    start(("START"))
    a1["DetectObject"]
    a2["PlanGrasp<br/><small>retry ×3</small>"]
    a3["MoveToPregrasp"]
    a4["OpenGripper"]
    a5["ApproachObject"]
    a6["CloseGripper"]
    a7["LiftObject"]
    a8["SafeRelease"]
    a9["AbortToHome"]
    a10["MoveToPlace"]
    a11["Release"]
    a12["Retreat"]
    a13["MoveToHome"]
    success(["SUCCESS"])
    failure(["FAILURE"])
    start --> a1
    a1 -->|"success and IsObjectReachable"| a2
    a1 -->|"success and not IsObjectReachable"| a8
    a1 -.->|"failure"| a8
    a2 -->|"success"| a3
    a2 -.->|"failure"| a8
    a3 -->|"success"| a4
    a3 -.->|"failure"| a8
    a4 -->|"success"| a5
    a4 -.->|"failure"| a8
    a5 -->|"success"| a6
    a5 -.->|"failure"| a8
    a6 -->|"success and IsObjectGrasped"| a7
    a6 -->|"success and not IsObjectGrasped"| a8
    a6 -.->|"failure"| a8
    a7 -->|"success"| a10
    a7 -.->|"failure"| a8
    a8 -->|"success"| a9
    a8 -.->|"failure"| failure
    a9 -->|"success"| failure
    a9 -.->|"failure"| failure
    a10 -->|"success"| a11
    a10 -.->|"failure"| failure
    a11 -->|"success"| a12
    a11 -.->|"failure"| failure
    a12 -->|"success"| a13
    a12 -.->|"failure"| failure
    a13 -->|"success"| success
    a13 -.->|"failure"| failure
    classDef start fill:#1b1813,stroke:#1b1813,stroke-width:1.5px,color:#f5f0e9
    classDef action fill:#fdfbf9,stroke:#1b1813,stroke-width:1.5px,color:#1b1813
    classDef success fill:#107550,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    classDef failure fill:#b93917,stroke:#fdfbf9,stroke-width:2px,color:#fdfbf9
    class start start
    class a1,a2,a3,a4,a5,a6,a7,a8,a9,a10,a11,a12,a13 action
    class success success
    class failure failure
    linkStyle 0 stroke:#1b1813,stroke-width:1.75px
    linkStyle 1,2,4,6,8,10,12,13,15,17,19,21,23,25,27 stroke:#107550,stroke-width:1.75px
    linkStyle 3,5,7,9,11,14,16,18,20,22,24,26,28 stroke:#b93917,stroke-width:1.75px,stroke-dasharray:7 4
```

## Adding an example

Good examples are small (under about 30 nodes), use names any robotics
engineer would recognise, and show one or two things worth noticing. Declare
every custom node in `<TreeNodesModel>`, add the expected graph to
`tests/unit/test_examples.py`, then refresh the graphs in the docs:

```console
$ uv run python scripts/update_docs_graphs.py
```
