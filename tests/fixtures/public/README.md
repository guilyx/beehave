# Public test fixtures

Beehave's tests run only on publicly available behaviour trees that carry permissive licences. Every XML file in this folder is a **byte-identical copy** of an upstream file. Do not edit, reformat or re-indent them. The directory layout below each source folder mirrors the upstream repository, so relative `<include path="…">` references still resolve. Each source folder contains the upstream licence text. The tables below give, for every file, the original URL, the pinned commit, the licence, the copyright holder, the git blob id (from `git hash-object`, which equals the upstream blob id) and the features the file exercises.

## Sources at a glance

| Folder | Upstream | Revision | Format | Licence | Licence file here |
|---|---|---|---|---|---|
| `btcpp-v3/` | [BehaviorTree/BehaviorTree.CPP](https://github.com/BehaviorTree/BehaviorTree.CPP) | tag `3.8.8` = tip of branch `v3.8`, commit `9d624dc7797b4752e5f8616793ffcee4b540a185` | v3 | MIT | `btcpp-v3/LICENSE` (upstream `LICENSE`, verbatim) |
| `groot/` | [BehaviorTree/Groot](https://github.com/BehaviorTree/Groot) (Groot 1, "compatible only with BehaviorTree.CPP 3.8.x") | branch `master`, commit `70973d004365f16d47a8c7bd9c5d84fa0bb9d05d` | v3 | MIT | `groot/LICENSE` (see note) |
| `nav2/` | [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | branch `humble`, commit `3c3db59d6969d8ecee8e68468693d006397f4a0c` | v3 | Apache-2.0 (per package `package.xml`) | `nav2/LICENSE` (upstream, verbatim) + `nav2/LICENSE-2.0.txt` |
| `v4/btcpp/` | [BehaviorTree/BehaviorTree.CPP](https://github.com/BehaviorTree/BehaviorTree.CPP) | branch `master`, commit `03ec870a07b384f0766bbfe81f77c64a9f994a2b` | v4 | MIT | `v4/btcpp/LICENSE` (upstream, verbatim) |
| `v4/nav2-jazzy/` | [ros-navigation/navigation2](https://github.com/ros-navigation/navigation2) | branch `jazzy`, commit `645abd95f2be02a13ca539b29c2ddc065db34f89` | v4 | Apache-2.0 (per package `package.xml`) | `v4/nav2-jazzy/LICENSE` (upstream, verbatim) + `LICENSE-2.0.txt` |

Licence notes:

- **BehaviorTree.CPP:** the upstream `LICENSE` is MIT with "Copyright (c) 2015 - 2018 Michele Colledanchise". Source files additionally carry "Copyright (C) 2018-2020 Davide Faconti". The XML fixtures themselves have no per-file notice.
- **Groot:** the repository has **no separate LICENSE file**. Its MIT licence and copyright notice are in the "Licence" section of `README.md`. `groot/LICENSE` is a verbatim copy of lines 72–90 of that README at the commit above, and the copyright holder is the one named in that notice. `package.xml` also declares `<license>MIT</license>`.
- **Nav2:** the upstream top-level `LICENSE` is a pointer file. It says that each package's `package.xml` gives that package's licence, and that unmarked files are Apache-2.0. Both packages used here (`nav2_bt_navigator`, `nav2_behavior_tree`) declare `Apache-2.0` in their `package.xml` on both branches. The XML files carry no per-file copyright notice, so the copyright holders are the Nav2 contributors. `LICENSE-2.0.txt` is the canonical Apache License 2.0 text from <https://www.apache.org/licenses/LICENSE-2.0.txt> (SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`).

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

## v4 fixtures (for version detection)

These files must be **refused** by the Phase 1 parser with a clear "BT.CPP v4 format detected" message.

| File | Original URL | Blob | Licence / holder | Detection signal |
|---|---|---|---|---|
| `v4/btcpp/examples/test_files/log_test.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/03ec870a07b384f0766bbfe81f77c64a9f994a2b/examples/test_files/log_test.xml> | `bc7dc59ebf98` | MIT, as `btcpp-v3/` | `BTCPP_format="4"`, the v4-only node `Sleep`, and `name` on `SubTree`. |
| `v4/btcpp/examples/test_files/Check.xml` | <https://github.com/BehaviorTree/BehaviorTree.CPP/blob/03ec870a07b384f0766bbfe81f77c64a9f994a2b/examples/test_files/Check.xml> | `8066d5ea1edb` | MIT, as `btcpp-v3/` | **No `BTCPP_format` marker**, but uses `SequenceWithMemory`. Tests detection without a marker. It is the v4 counterpart of `btcpp-v3/examples/test_files/Check.xml`. |
| `v4/nav2-jazzy/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml` | <https://github.com/ros-navigation/navigation2/blob/645abd95f2be02a13ca539b29c2ddc065db34f89/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_and_recovery.xml> | `f135107c5b1c` | Apache-2.0, Nav2 contributors | `BTCPP_format="4"`. The same tree as the humble v3 fixture, for paired tests. |
| `v4/nav2-jazzy/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml` | <https://github.com/ros-navigation/navigation2/blob/645abd95f2be02a13ca539b29c2ddc065db34f89/nav2_bt_navigator/behavior_trees/navigate_to_pose_w_replanning_goal_patience_and_recovery.xml> | `0b9bccf3abe8` | Apache-2.0, Nav2 contributors | `BTCPP_format="4"` and `SequenceWithMemory`, the v4 name of the `SequenceStar` in the humble version. |

## Known gaps

- **No public, permissively licensed, standalone v3 XML file using `<SubTreePlus>` / `__autoremap` / `__shared_blackboard` was found.** The searches covered BehaviorTree.CPP (all 3.x tags), Groot, BehaviorTree.ROS, Nav2 humble and navigation2_tutorials, plus web searches. BehaviorTree.CPP 3.8.8 contains `SubTreePlus` trees only as C++ string literals (`tests/gtest_subtree.cpp`, and the doc comment in `include/behaviortree_cpp_v3/decorators/subtree_node.h`). `examples/t06_subtree_port_remapping.cpp` contains a classic `SubTree` remapping example, also as a string literal. Tests for `SubTreePlus` remapping therefore need hand-written fixtures, which belong in a separate folder, not here.
- Nav2 humble trees contain no subtrees. Subtree coverage comes from `btcpp-v3/` and `groot/`.

## Verifying integrity

```sh
# Each XML fixture's git blob id must match the "Blob" column (first 12 hex digits).
git hash-object tests/fixtures/public/nav2/nav2_bt_navigator/behavior_trees/follow_point.xml
```
