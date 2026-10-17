# Public test fixtures

Beehave's tests run only on publicly available behaviour trees that carry permissive licences. Every XML file in this folder is a **byte-identical copy** of an upstream file. Do not edit, reformat or re-indent them. The directory layout below each source folder mirrors the upstream repository, so relative `<include path="…">` references still resolve. Each source folder contains the upstream licence text. The tables below give, for every file, the original URL, the pinned commit, the licence, the copyright holder, the git blob id (from `git hash-object`, which equals the upstream blob id) and the features the file exercises.

## Sources at a glance

| Folder | Upstream | Revision | Format | Licence | Licence file here |
|---|---|---|---|---|---|
| `btcpp-v3/` | [BehaviorTree/BehaviorTree.CPP](https://github.com/BehaviorTree/BehaviorTree.CPP) | tag `3.8.8` = tip of branch `v3.8`, commit `9d624dc7797b4752e5f8616793ffcee4b540a185` | v3 | MIT | `btcpp-v3/LICENSE` (upstream `LICENSE`, verbatim) |
| `groot/` | [BehaviorTree/Groot](https://github.com/BehaviorTree/Groot) (Groot 1, "compatible only with BehaviorTree.CPP 3.8.x") | branch `master`, commit `70973d004365f16d47a8c7bd9c5d84fa0bb9d05d` | v3 | MIT | `groot/LICENSE` (see note) |
| `nav2/` | [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | branch `humble`, commit `3c3db59d6969d8ecee8e68468693d006397f4a0c` | v3 | Apache-2.0 (per package `package.xml`) | `nav2/LICENSE` (upstream, verbatim) + `nav2/LICENSE-2.0.txt` |
| `v4/btcpp/` | [BehaviorTree/BehaviorTree.CPP](https://github.com/BehaviorTree/BehaviorTree.CPP) | branch `master`, commit `03ec870a07b384f0766bbfe81f77c64a9f994a2b` | v4 | MIT | `v4/btcpp/LICENSE` (upstream, verbatim) |
| `v4/nav2-jazzy/` | [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | branch `jazzy`, commit `58e4019eb149ed4387938d9cd13f38659b86f754` | v4 | Apache-2.0 (per package `package.xml`) | `v4/nav2-jazzy/LICENSE` (upstream, verbatim) + `LICENSE-2.0.txt` + `nav2_docking/LICENSE` (upstream, verbatim) |
| `v4/btcpp-ros2/` | [BehaviorTree/BehaviorTree.ROS2](https://github.com/BehaviorTree/BehaviorTree.ROS2) | branch `humble` (default), commit `6c6aa078ee7bc52fec98984bed4964556abf5beb` | v4 | Apache-2.0 (see note) | `v4/btcpp-ros2/LICENSE` (upstream, verbatim) |
| `v4/auto-apms/` | [AutoAPMS/auto-apms](https://github.com/AutoAPMS/auto-apms) | branch `master`, commit `86a25f90ffa49154fbe177ca99b3232ace407ccf` | v4 | Apache-2.0 | `v4/auto-apms/LICENSE` (upstream, verbatim) |
| `v4/scan-n-plan/` | [ros-industrial-consortium/scan_n_plan_workshop](https://github.com/ros-industrial-consortium/scan_n_plan_workshop) | branch `master`, commit `aae82a946f94290bf354b6c3e3f3807083fb7f32` | v4 | Apache-2.0 (see note) | `v4/scan-n-plan/LICENSE` (upstream, verbatim) |
| `v4/litebt/` | [dongnh/LiteBT](https://github.com/dongnh/LiteBT) | branch `main`, commit `e9e0a3d137c3f67176c61e4b9d65bb1d84f88d85` | v4 | MIT | `v4/litebt/LICENSE` (upstream, verbatim) |

Licence notes:

- **BehaviorTree.CPP:** the upstream `LICENSE` is MIT with "Copyright (c) 2015 - 2018 Michele Colledanchise". Source files additionally carry "Copyright (C) 2018-2020 Davide Faconti". The XML fixtures themselves have no per-file notice.
- **Groot:** the repository has **no separate LICENSE file**. Its MIT licence and copyright notice are in the "Licence" section of `README.md`. `groot/LICENSE` is a verbatim copy of lines 72–90 of that README at the commit above, and the copyright holder is the one named in that notice. `package.xml` also declares `<license>MIT</license>`.
- **Nav2:** the upstream top-level `LICENSE` is a pointer file. It says that each package's `package.xml` gives that package's licence, and that unmarked files are Apache-2.0. Both packages used here (`nav2_bt_navigator`, `nav2_behavior_tree`) declare `Apache-2.0` in their `package.xml` on both branches. The XML files carry no per-file copyright notice, so the copyright holders are the Nav2 contributors. `LICENSE-2.0.txt` is the canonical Apache License 2.0 text from <https://www.apache.org/licenses/LICENSE-2.0.txt> (SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`). The jazzy docking example comes from the package `opennav_docking_bt`, which also declares `Apache-2.0`. Its folder `nav2_docking/` ships its own copy of the Apache text, kept here as `v4/nav2-jazzy/nav2_docking/LICENSE`.
- **BehaviorTree.ROS2:** the repository `LICENSE` is the Apache License 2.0 with the copyright lines of the original authors, and the README says the project keeps "the same license and copyright". Its `package.xml` files declare `MIT`. Both are permissive. `LICENSE` is treated as authoritative.
- **AutoAPMS:** `LICENSE` is the Apache License 2.0, and every package declares `Apache-2.0`.
- **scan_n_plan_workshop (ROS-Industrial):** `LICENSE` is the Apache License 2.0. The `package.xml` of `snp_application` declares `Apache 2.0n` (an upstream typo).
- **LiteBT:** `LICENSE` is MIT.

## v3 fixtures

### `btcpp-v3/` (BehaviorTree.CPP 3.8.8, MIT; copyright Michele Colledanchise, Davide Faconti and contributors)

| File | Original URL | Blob | What it exercises |
|---|---|---|---|
| `examples/test_files/subtree_test.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/examples/test_files/subtree_test.xml> | `b9ccccf6b79f` | `<include>` of two files, one in a subdirectory. **Compact subtree references** (`<CheckStatus/>`, `<SayStuff/>`), which v3.8 itself rejects (see `docs/research/btcpp-v3-xml.md` §2.5). Expected: warn and accept. |
| `examples/test_files/Check.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/examples/test_files/Check.xml> | `50a2e9ba141a` | included file. `SequenceStar` with explicit `<Action ID>` children. `<root>` without `main_tree_to_execute`. |
| `examples/test_files/subtrees/Talk.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/examples/test_files/subtrees/Talk.xml> | `1d2020122cb7` | included file in a subdirectory. `SequenceStar`, literal port value. |
| `tests/trees/parent_include_child_include_parent.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/tests/trees/parent_include_child_include_parent.xml> | `f6234da7c31c` | nested includes. The child includes `../parent_no_include.xml`, so paths are relative to the **including** file. `<SubTree ID>` chain of three trees, `AlwaysSuccess`. |
| `tests/trees/child/child_include_parent.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/tests/trees/child/child_include_parent.xml> | `8312376df190` | (dependency of the above) |
| `tests/trees/parent_no_include.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/tests/trees/parent_no_include.xml> | `dedc05144cb8` | (dependency of the above). The smallest possible tree. |

### `groot/` (Groot 1 test data, MIT; copyright holder as in `groot/LICENSE`)

| File | Original URL | Blob | What it exercises |
|---|---|---|---|
| `test_data/crossdoor_with_subtree.xml` | <https://github.com/BehaviorTree/Groot/blob/70973d004365f16d47a8c7bd9c5d84fa0bb9d05d/test_data/crossdoor_with_subtree.xml> | `19f9f0f2d1cf` | the canonical "cross door" example. `<?xml?>` declaration, `<!-- ////////// -->` separators, `Fallback`, `Sequence`, explicit `<Condition ID>` / `<Action ID>`, `Inverter`, `RetryUntilSuccessful num_attempts="4"`, `<SubTree ID>` without ports, `<TreeNodesModel>` declaring conditions and a subtree. |
| `test_data/subtree_with_remapping.xml` | <https://github.com/BehaviorTree/Groot/blob/70973d004365f16d47a8c7bd9c5d84fa0bb9d05d/test_data/subtree_with_remapping.xml> | `77b689428973` | **classic v3 `SubTree` remapping with a plain key** (`message="myMsg"`). The **same subtree instantiated twice**, so flattening must create two copies. `SetBlackboard`. Subtree port model in `<TreeNodesModel>`. |
| `test_data/test_xml_key_reordering_issue.xml` | <https://github.com/BehaviorTree/Groot/blob/70973d004365f16d47a8c7bd9c5d84fa0bb9d05d/test_data/test_xml_key_reordering_issue.xml> | `e2385d648f37` | several subtrees with multi-port classic remapping. `Fallback` over three `Sequence(Condition, Action)` guards (`OnAir`/`Fly`, `OnGround`/`Roll`, `OnWater`/`Swim`): a good guard-collection test. Literal containing `&quot;`. A port name typo upstream (`contratint_c`). |
| `test_data/show_all.xml` | <https://github.com/BehaviorTree/Groot/blob/70973d004365f16d47a8c7bd9c5d84fa0bb9d05d/test_data/show_all.xml> | `d2b1f149842c` | many built-ins in one tree: `ReactiveFallback`, `Repeat num_cycles="1"`, `AlwaysFailure`, `SequenceStar`, `RetryUntilSuccessful num_attempts="1"`, `BlackboardCheckString` with **empty** port values, `AlwaysSuccess`, `Inverter(ForceFailure(ForceSuccess(SetBlackboard)))`, `ReactiveSequence`. |

### `nav2/` (Nav2 humble, Apache-2.0; copyright Nav2 contributors)

| File | Original URL | Blob | What it exercises |
|---|---|---|---|
| `nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml` | <https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml> | `2396b844aedc` | Nav2's default tree. A comment before `<root>`. **Custom controls** `RecoveryNode`, `PipelineSequence`, `RoundRobin`, the custom decorator `RateController`, the condition `GoalUpdated`, `ReactiveFallback`, `{goal}`/`{path}` keys, and an instance `name` equal to another node's ID. |
| `nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml` | <https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml> | `6b5883bfe70a` | `ReactiveSequence`, custom decorator `PathLongerOnApproach`, `RetryUntilSuccessful num_attempts="1"` around `SequenceStar`, `CancelControl`. |
| `nav2_bt_navigator/behavior_trees/navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml` | <https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_bt_navigator/behavior_trees/navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml> | `d21efa3b4bf2` | `Fallback(ReactiveSequence(Inverter(GlobalUpdatedGoal), IsPathValid), ComputePathToPose)`: a negated condition guard. `RecoveryNode` nesting. |
| `nav2_bt_navigator/behavior_trees/follow_point.xml` | <https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_bt_navigator/behavior_trees/follow_point.xml> | `ffae8d9b2ab2` | **`KeepRunningUntilFailure`** (success continuation unreachable), the custom decorator `GoalUpdater` with input and output ports, `TruncatePath`. |
| `nav2_bt_navigator/behavior_trees/odometry_calibration.xml` | <https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_bt_navigator/behavior_trees/odometry_calibration.xml> | `49000e14fa65` | **`Repeat num_cycles="3"`** around an 8-action `Sequence` (a loop edge), and a `name` containing spaces. The `Spin` port `is_recovery` is **not declared** in the humble models file, so model checks must warn, not fail. |
| `nav2_behavior_tree/nav2_tree_nodes.xml` | <https://github.com/ros-navigation/navigation2/blob/3c3db59d6969d8ecee8e68468693d006397f4a0c/nav2_behavior_tree/nav2_tree_nodes.xml> | `1a2e3d7be66f` | a **models-only** file (`<root><TreeNodesModel>` with no `<BehaviorTree>`). It declares the kind of every Nav2 node: 29 actions, 12 conditions, 3 controls, 7 decorators. Use it as the model input for the Nav2 trees. |

## v4 fixtures

These files are BehaviorTree.CPP **v4** trees, the inputs for the v4 parser. The reference for what they mean is `docs/research/btcpp-v4-xml.md`. Until the v4 parser exists, the v3 parser must **refuse** every file below with a clear "BT.CPP v4 format detected" message. The one exception is `nav2-jazzy/nav2_docking/…/application_example.xml`: it has no `BTCPP_format` marker and no v4-only construct, so it cannot be told apart from v3 (see its row).

Unless a row says otherwise, every file loads in BT.CPP 4.10.0 once its user nodes are registered. The rows marked **invalid** do not load in BT.CPP itself. They are kept as error-handling inputs, and the expected error is given.

### Paired v3 and v4 fixtures

These v4 files have a v3 counterpart in this folder. "Same graph" means the v3 parser on the v3 file and the v4 parser on the v4 file must give the same action graph. For the Nav2 pairs, "same graph modulo selectors" means: equal after removing the two jazzy-only actions `ControllerSelector` and `PlannerSelector` (the first two children of the top `PipelineSequence`) and ignoring port values.

| v4 file | v3 twin | Relation |
|---|---|---|
| `btcpp/examples/test_files/Check.xml` | `btcpp-v3/examples/test_files/Check.xml` | **same graph**. Only `SequenceStar` → `SequenceWithMemory` and whitespace differ. |
| `btcpp/examples/test_files/subtrees/Talk.xml` | `btcpp-v3/examples/test_files/subtrees/Talk.xml` | **same graph**. `SequenceStar` → `SequenceWithMemory`, marker added, `main_tree_to_execute` removed. |
| `btcpp/examples/test_files/subtree_test.xml` | `btcpp-v3/examples/test_files/subtree_test.xml` | **same graph**. Marker added, `main_tree_to_execute="BehaviorTree"` removed: the main tree is now the file's only local tree. |
| `btcpp/tests/trees/parent_include_child_include_parent.xml`, `btcpp/tests/trees/child/child_include_parent.xml`, `btcpp/tests/trees/parent_no_include.xml` | the same paths under `btcpp-v3/` | **same graph**. Only the marker differs. |
| `nav2-jazzy/nav2_bt_navigator/behavior_trees/odometry_calibration.xml` | `nav2/…/odometry_calibration.xml` | **same graph**. Only the marker differs. |
| `nav2-jazzy/…/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml` | `nav2/…/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml` | **same graph modulo selectors**. Also `SequenceStar` → `SequenceWithMemory`, `planner_id`/`controller_id` become `{selected_planner}`/`{selected_controller}`, new `error_code_id` outputs, `Wait` 5 → 5.0, `BackUp` speed 0.05 → 0.15. |
| `nav2-jazzy/…/navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml` | `nav2/…/navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml` | **same graph modulo selectors**. Port values as above. |
| `nav2-jazzy/…/follow_point.xml` | `nav2/…/follow_point.xml` | **same graph modulo selectors**. Port values as above. |
| `nav2-jazzy/…/navigate_to_pose_w_replanning_and_recovery.xml` | `nav2/…/navigate_to_pose_w_replanning_and_recovery.xml` | **different graphs.** Besides the selectors and ports, jazzy guards each contextual `ClearEntireCostmap` with `Sequence(WouldAPlannerRecoveryHelp \| WouldAControllerRecoveryHelp, …)` and wraps the recovery `ReactiveFallback` in `Sequence(Fallback(WouldAControllerRecoveryHelp, WouldAPlannerRecoveryHelp), …)`. Earlier notes in this file and in `docs/research/btcpp-v3-vs-v4.md` §3 called this pair "the same tree". It is not. |

The seven other jazzy trees also exist on Nav2 `humble`, but their humble versions are not fixtures here.

### `v4/btcpp/` (BehaviorTree.CPP `master` @ `03ec870`, MIT; copyright Michele Colledanchise, Davide Faconti and contributors)

Every standalone XML file in `examples/` and `tests/` of `master`, plus the four seed files of the XML fuzzer. URLs are `https://github.com/BehaviorTree/BehaviorTree.CPP/blob/03ec870a07b384f0766bbfe81f77c64a9f994a2b/<file>`.

| File | Blob | What it exercises |
|---|---|---|
| `examples/test_files/log_test.xml` | `bc7dc59ebf98` | `BTCPP_format="4"`, the v4-only node `Sleep`, `name` on `SubTree`, a `<TreeNodesModel>` written by Groot2 (`editable="true"`). |
| `examples/test_files/Check.xml` | `8066d5ea1edb` | **No `BTCPP_format` marker**, but `SequenceWithMemory` with explicit `<Action ID>` children. Detection without a marker. |
| `examples/test_files/subtree_test.xml` | `ff8c6caeae3e` | Two `<include>`s, one into `subtrees/`. **Compact subtree references** `<CheckStatus/>`, `<SayStuff/>`. **Invalid in BT.CPP:** "Node not recognized: CheckStatus". No upstream code loads this file. Expected in Beehave: warn and accept, as in v3. No `main_tree_to_execute`. |
| `examples/test_files/subtrees/Talk.xml` | `a8b9edf0f2f6` | Included file. `SequenceWithMemory`, explicit `<Action ID>`, a literal port value. |
| `tests/trees/parent_no_include.xml` | `73ced4dd81cf` | The smallest tree. `main_tree_to_execute = "…"` with spaces around `=`. Loaded by upstream `gtest_factory.cpp`. |
| `tests/trees/parent_include_child.xml` | `39695dd1de03` | Include into a child directory. `<SubTree ID>`. |
| `tests/trees/parent_include_child_include_child.xml` | `215cdac44497` | Include chain parent → `child/` → `child/child/`. |
| `tests/trees/parent_include_child_include_parent.xml` | `49a8d9128067` | Include chain that climbs back with `../`. Relative paths resolve against the **including** file. |
| `tests/trees/parent_include_child_include_sibling.xml` | `c5625e522c4e` | Include chain with a sibling include. |
| `tests/trees/child/child_include_child.xml` | `dcae8c341c70` | (dependency) includes `child/child_child_no_include.xml`. |
| `tests/trees/child/child_include_parent.xml` | `4600a00e19c5` | (dependency) includes `../parent_no_include.xml`. |
| `tests/trees/child/child_include_sibling.xml` | `c39a6e2950c8` | (dependency) includes `child_no_include.xml`. |
| `tests/trees/child/child_no_include.xml` | `cdd98f7df0ee` | (dependency) a leaf tree. |
| `tests/trees/child/child/child_child_no_include.xml` | `64f93ac7c4fa` | (dependency) a leaf tree. |
| `fuzzing/corpus/bt_corpus/corpus1.xml` | `e625cb41b7f2` | Valid. `Sequence(AlwaysSuccess)` with instance names, no `main_tree_to_execute`. |
| `fuzzing/corpus/bt_corpus/corpus2.xml` | `461e53c642ba` | **Invalid:** "a port with name [timeout_ms] is found in the XML (\<Timeout\>…) but not in the providedPorts()". `Timeout` without its required `msec`. |
| `fuzzing/corpus/bt_corpus/corpus3.xml` | `e21ea8adfd87` | **Invalid:** "The attribute [ID] of tag \<SubTree\> must not use the name of a registered Node" (`<SubTree ID="SubTree">`, which is also undefined). `SetBlackboard` with an unknown port `key`. `_autoremap="true"`. |
| `fuzzing/corpus/bt_corpus/corpus4.xml` | `3111d8be4c51` | **Invalid:** "The node 'ForceSuccess' must have exactly 1 child" (decorators with no child). |

### `v4/nav2-jazzy/` (Nav2 `jazzy` @ `58e4019`, Apache-2.0; copyright Nav2 contributors)

All 12 behaviour trees of `nav2_bt_navigator/behavior_trees/`, the matching models file, and the docking example tree. URLs are `https://github.com/ros-navigation/navigation2/blob/58e4019eb149ed4387938d9cd13f38659b86f754/<file>`. The two trees imported earlier were pinned at `645abd9`. Between `645abd9` and `58e4019` only the packages' `package.xml` versions changed, so those blobs are unchanged.

| File | Blob | What it exercises |
|---|---|---|
| `nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml` | `f135107c5b1c` | Nav2's default tree. `RecoveryNode`, `PipelineSequence`, `RoundRobin`, `RateController`, the conditions `WouldAPlannerRecoveryHelp`, `WouldAControllerRecoveryHelp`, `GoalUpdated`, and `error_code_id` output ports. |
| `nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml` | `0b9bccf3abe8` | `SequenceWithMemory`, `PathLongerOnApproach`, `RetryUntilSuccessful num_attempts="1"`, `CancelControl`. |
| `nav2_bt_navigator/behavior_trees/navigate_w_recovery_and_replanning_only_if_path_becomes_invalid.xml` | `3575740252dc` | `ReactiveSequence(Inverter(GlobalUpdatedGoal), IsPathValid)`: a negated condition guard. |
| `nav2_bt_navigator/behavior_trees/navigate_through_poses_w_replanning_and_recovery.xml` | `501034d67400` | `ReactiveSequence(RemovePassedGoals, ComputePathThroughPoses)`: two actions under a reactive node. |
| `nav2_bt_navigator/behavior_trees/nav_to_pose_with_consistent_replanning_and_if_path_becomes_invalid.xml` | `b2cb86113e59` | `Fallback(ReactiveSequence(Inverter(PathExpiringTimer), Inverter(GlobalUpdatedGoal), IsPathValid), ComputePathToPose)`: a three-condition guard with two negations. |
| `nav2_bt_navigator/behavior_trees/navigate_w_replanning_distance.xml` | `16f7ede4b3e2` | custom decorator `DistanceController`. |
| `nav2_bt_navigator/behavior_trees/navigate_w_replanning_speed.xml` | `e0d5d6a5a415` | custom decorator `SpeedController`. |
| `nav2_bt_navigator/behavior_trees/navigate_w_replanning_time.xml` | `11332fb24e9e` | `RateController` only. The smallest Nav2 tree. |
| `nav2_bt_navigator/behavior_trees/navigate_w_replanning_only_if_goal_is_updated.xml` | `a214c9b64fd1` | custom decorator `GoalUpdatedController`. |
| `nav2_bt_navigator/behavior_trees/navigate_w_replanning_only_if_path_becomes_invalid.xml` | `effe9a2bf82c` | `Fallback(ReactiveSequence(Inverter(GlobalUpdatedGoal), IsPathValid), …)`. |
| `nav2_bt_navigator/behavior_trees/follow_point.xml` | `9f55ecd66ec3` | `KeepRunningUntilFailure`, `GoalUpdater` with input and output ports, `TruncatePath`. |
| `nav2_bt_navigator/behavior_trees/odometry_calibration.xml` | `fdc459f40ffd` | `Repeat num_cycles="3"` around an 8-action `Sequence`. Exact twin of the humble file. |
| `nav2_behavior_tree/nav2_tree_nodes.xml` | `c84612199e1a` | **Models-only** file with `BTCPP_format="4"`: 38 actions, 17 conditions, 3 controls, 7 decorators. It declares every user node of the 12 trees above, and the docking nodes. |
| `nav2_docking/opennav_docking_bt/behavior_trees/application_example.xml` | `509c73217210` | **No marker and no v4-only construct**, so it reads as v3. **Invalid in BT.CPP:** "Node not recognized: inverter" (lower case `<inverter>`). A comment before `<root>` contains XML-like text. `ForceSuccess`, `ReactiveFallback`. |
| `nav2_docking/LICENSE` | `261eeb9e9f8b` | The Apache-2.0 text shipped in `nav2_docking/` upstream. |

### `v4/btcpp-ros2/` (BehaviorTree.ROS2 `humble` @ `6c6aa07`, Apache-2.0; copyright holders as in `btcpp-ros2/LICENSE`)

URLs are `https://github.com/BehaviorTree/BehaviorTree.ROS2/blob/6c6aa078ee7bc52fec98984bed4964556abf5beb/<file>`. `humble` is the repository's default branch, and it targets BT.CPP 4.

| File | Blob | What it exercises |
|---|---|---|
| `btcpp_ros2_samples/behavior_trees/cross_door.xml` | `d2cba2446824` | The cross-door tree in v4. `<SubTree ID="DoorClosed"/>` points to a tree in **another file with no `<include>`**: the executor loads the whole folder. Load both files together. `Fallback(Inverter(IsDoorClosed), …)`. No models: `IsDoorClosed` must come from the config. |
| `btcpp_ros2_samples/behavior_trees/door_closed.xml` | `b328a349b6fa` | (dependency) `Fallback`, `RetryUntilSuccessful num_attempts="5"`. |
| `btcpp_ros2_samples/behavior_trees/sleep_action.xml` | `2e83ece731d4` | `Timeout msec="1500"` around a ROS action node, inside a `Fallback`. |
| `LICENSE` | `5f09852921d6` | upstream licence, verbatim |

### `v4/auto-apms/` (AutoAPMS `master` @ `86a25f9`, Apache-2.0; copyright holders as stated upstream)

URLs are `https://github.com/AutoAPMS/auto-apms/blob/86a25f90ffa49154fbe177ca99b3232ace407ccf/<file>`.

| File | Blob | What it exercises |
|---|---|---|
| `auto_apms_mission/config/orchestrator_base.xml` | `2fe4bfaa37be` | The richest v4 fixture: `_failureIf`, `_while`, `_skipIf`, `_onSuccess`, `_onFailure`, `_onHalted`, `_description`; `<SubTree event_id="{=}">`; multi-statement `Script` with `&apos;` and `&#10;` entities; `ScriptCondition` with `!=` and `==` on strings; `Parallel success_count="1" failure_count="1"`; `KeepRunningUntilFailure`; `RetryUntilSuccessful num_attempts="-1"`; `ReactiveFallback` over guarded children; `SequenceWithMemory`; 9 trees; a `<TreeNodesModel>` with 7 entries. |
| `auto_apms_examples/behavior/demo.xml` | `7241a6530cac` | Two trees, **no `main_tree_to_execute`**. `Sleep`, `Script`, `_post` with string concatenation `+`, `WasEntryUpdated` with `_onSuccess`/`_onFailure`. |
| `auto_apms_examples/behavior/simple_skill_tree.xml` | `9e1cc8075c75` | Root-blackboard reads `@msg`, `@n_times` in post-conditions. `<TreeNodesModel>` declaring two actions with typed ports. |
| `auto_apms_examples/behavior/my_behavior_tree.xml` | `1c8f2b9cccb5` | An **empty** `<TreeNodesModel/>`. `ScriptCondition code="true"`. No `main_tree_to_execute`, a single tree. |
| `auto_apms_behavior_tree/test/resource/include_e2e.xml` | `c882f88cf3ec` | Six trees, a helper subtree shared by two of them, built-in nodes only. |
| `auto_apms_behavior_tree/test/resource/test_tree.xml` | `1e8b6cac0aa4` | The smallest v4 file with an `<?xml?>` declaration. |
| `LICENSE` | `261eeb9e9f8b` | upstream licence, verbatim |

### `v4/scan-n-plan/` (ROS-Industrial `scan_n_plan_workshop` `master` @ `aae82a9`, Apache-2.0; copyright holders as stated upstream)

URL: `https://github.com/ros-industrial-consortium/scan_n_plan_workshop/blob/aae82a946f94290bf354b6c3e3f3807083fb7f32/snp_application/config/snp.xml`.

| File | Blob | What it exercises |
|---|---|---|
| `snp_application/config/snp.xml` | `6dcaa5411cae` | A real application with six trees and **no `main_tree_to_execute`** (the application picks `main` or `go_home_main`). `_autoremap="true"` subtrees with extra remaps; `_skipIf="skip_scan"` with a bare boolean; `_onFailure="skip_scan=false"` (`=` on an existing key); `_description`; user controls and decorators (`SNPSequenceWithMemory`, `Progress`, `SetPage`); `ReactiveSequence` with a button monitor as an abort guard; `KeepRunningUntilFailure`; a 25-entry `<TreeNodesModel>`. |
| `LICENSE` | `4720f17f0471` | upstream licence, verbatim |

### `v4/litebt/` (LiteBT `main` @ `e9e0a3d`, MIT; copyright holder as in `litebt/LICENSE`)

LiteBT is a separate behaviour-tree engine that reads BT.CPP 4 XML. Its test suite runs each corpus tree on **BT.CPP 4.10.0** and on LiteBT, and compares the traces. The XML comment at the top of each file says which BT.CPP behaviour the tree pins down. That makes these files small, targeted probes of v4 semantics. Every user leaf is an action (the upstream harness registers each unknown leaf as an action). URLs are `https://github.com/dongnh/LiteBT/blob/e9e0a3d137c3f67176c61e4b9d65bb1d84f88d85/<file>`. Not imported: `b8-loop.xml` and `tests/LiteBT.Tests/Trees/reward-stack.xml`, which use a `<Loop>` node that BT.CPP does not have, and the JSON scenario files.

| File | Blob | What it exercises |
|---|---|---|
| `tests/LiteBT.Tests/DifferentialCorpus/a1-sequence.xml` | `2677c1378307` | `Sequence`, `Fallback`, `SequenceWithMemory` side by side. |
| `tests/LiteBT.Tests/DifferentialCorpus/a2-reactive.xml` | `e72fb5ed540f` | `ReactiveSequence` and `ReactiveFallback` with `ScriptCondition` guards, `_onHalted`. |
| `tests/LiteBT.Tests/DifferentialCorpus/a3-parallel.xml` | `ed2e9df60f85` | Four `Parallel` nodes with different `success_count`/`failure_count`, `_onHalted`. |
| `tests/LiteBT.Tests/DifferentialCorpus/a4-branch.xml` | `eb9dfc433d6a` | `IfThenElse` (2 and 3 children), `WhileDoElse` (2 and 3 children), `Switch3`. |
| `tests/LiteBT.Tests/DifferentialCorpus/a5-decorator.xml` | `bc5486be7ff9` | `Inverter`, `ForceSuccess`, `ForceFailure`, `KeepRunningUntilFailure`, and `Precondition` with `else` = FAILURE, SUCCESS and **SKIPPED**. |
| `tests/LiteBT.Tests/DifferentialCorpus/a6-script.xml` | `a10be3aeef49` | **All four pre-conditions and all four post-conditions**, `Script` with `:=`, `+=`, `*=` and a ternary, `ScriptCondition` with `\|\|`, `&&`, `!( … )` and a chained comparison `0 < n <= 14`. |
| `tests/LiteBT.Tests/DifferentialCorpus/a7-precond-order.xml` | `e78d2f0b4ae6` | The **evaluation order** of `_failureIf`, `_successIf`, `_skipIf` and `_while`: two or four pre-conditions on one node. |
| `tests/LiteBT.Tests/DifferentialCorpus/b1-repeat.xml` | `9ac7ffce33ea` | `Repeat`. |
| `tests/LiteBT.Tests/DifferentialCorpus/b2-retry.xml` | `48f750830d0c` | `RetryUntilSuccessful`. |
| `tests/LiteBT.Tests/DifferentialCorpus/b3-subtree.xml` | `b42b882ba710` | `SubTree` without remapping; a `Script` inside writes to the subtree's own blackboard. |
| `tests/LiteBT.Tests/DifferentialCorpus/b4-runonce.xml` | `e1bafc613b9c` | `RunOnce then_skip="true"`: SKIPPED from the second activation. |
| `tests/LiteBT.Tests/DifferentialCorpus/b5-subtree-local.xml` | `3633d744e6d3` | Keys local to a subtree instance. |
| `tests/LiteBT.Tests/DifferentialCorpus/b6-halt.xml` | `54ffe10dbc97` | `ReactiveSequence` halting a `SequenceWithMemory`. |
| `tests/LiteBT.Tests/DifferentialCorpus/b7-memory-yield.xml` | `8ac2dd5b8713` | `SequenceWithMemory` yielding RUNNING between children. |
| `tests/LiteBT.Tests/DifferentialCorpus/b10-async-fallback.xml` | `bc64a99735be` | `AsyncFallback`. |
| `tests/LiteBT.Tests/DifferentialCorpus/b11-subtree-forward.xml` | `b01d6a236ad0` | A subtree whose root is itself a `<SubTree>`: three trees chained. |
| `tests/LiteBT.Tests/DifferentialCorpus/f1-ifthenelse-stale.xml` | `510144f46da1` | Two-child `IfThenElse` whose condition fails. |
| `tests/LiteBT.Tests/DifferentialCorpus/f2-whiledoelse-strand.xml` | `aa17b13da261` | Two-child `WhileDoElse` whose condition turns false while the branch runs. |
| `tests/LiteBT.Tests/DifferentialCorpus/f3-entry-updated.xml` | `bea9a7f5ae60` | `SkipUnlessUpdated entry="{watched}"`. |
| `tools/btcpp-oracle/samples/tier-a.xml` | `d6c27acf3e71` | `Fallback`, `ReactiveSequence`, `Parallel`, `Precondition`, `Script`, `_skipIf` in one tree. |
| `tools/btcpp-oracle/samples/tier-a-controls.xml` | `1f48120eeca5` | `IfThenElse`, `WhileDoElse`, `Switch2`, `SequenceWithMemory`, `ReactiveFallback`, `Parallel`, `KeepRunningUntilFailure`, `_failureIf`, `_successIf`, `_onSuccess`, `_onFailure`, `_post`. |
| `tools/btcpp-oracle/samples/tier-b-async.xml` | `1081dfa10ec1` | `AsyncSequence`. |
| `tools/btcpp-oracle/samples/tier-b-repeat.xml` | `abaef2183e56` | `Repeat`. |
| `LICENSE` | `2dd12a088a8c` | upstream licence, verbatim |

### v4 gaps

- **No imported file uses `Switch4`–`Switch6`, `TryCatch`, `ParallelAll`, `LoopInt`/`LoopBool`/`LoopDouble`/`LoopString`, `WaitValueUpdate`, `UnsetBlackboard`, `Delay`, `Precondition else="RUNNING"` or a `{@key}` port value.** BT.CPP's own tests contain them only as C++ string literals (`tests/gtest_try_catch.cpp`, `tests/gtest_loop.cpp`, …). Tests for those nodes need hand-written trees, in a separate folder.
- **No public Groot2 project (`.btproj`) or Groot2 sample was found.** The Groot2 repository holds only a README.
- Candidates seen but not imported: `memristor/mep3` (Apache-2.0, about 50 v4 strategy trees with `_skipIf`, `_autoremap` and `Script`) and other robotics projects found by code search. They can be added the same way if more coverage is needed.

## Known gaps

- **No public, permissively licensed, standalone v3 XML file using `<SubTreePlus>` / `__autoremap` / `__shared_blackboard` was found.** The searches covered BehaviorTree.CPP (all 3.x tags), Groot, BehaviorTree.ROS, Nav2 humble and navigation2_tutorials, plus web searches. BehaviorTree.CPP 3.8.8 contains `SubTreePlus` trees only as C++ string literals (`tests/gtest_subtree.cpp`, and the doc comment in `include/behaviortree_cpp_v3/decorators/subtree_node.h`). `examples/t06_subtree_port_remapping.cpp` contains a classic `SubTree` remapping example, also as a string literal. Tests for `SubTreePlus` remapping therefore need hand-written fixtures, which belong in a separate folder, not here.
- Nav2 humble trees contain no subtrees. Subtree coverage comes from `btcpp-v3/` and `groot/`.

## Verifying integrity

```sh
# Each XML fixture's git blob id must match the "Blob" column (first 12 hex digits).
git hash-object tests/fixtures/public/nav2/nav2_bt_navigator/behavior_trees/follow_point.xml
```
