# Prior art: tools around behaviour-tree XML and BT analysis

This survey covers the existing tools that read, draw, check or verify behaviour trees, with a focus on BehaviorTree.CPP (BT.CPP) XML. For each tool it records what goes in, what comes out, and whether the tool inlines subtrees, computes the conditions under which an action runs (guards), or derives the action-to-action success/failure graph that Beehave calls the **action graph**. Every claim cites a source, and claims that could not be checked first-hand are marked. In short: the existing tools are editors and monitors (Groot, Groot2, the VS Code extensions), structure renderers (py_trees display, Nav2 `bt2img.py`), or model checkers that need their own input language (BehaVerify, BTCompiler, MoVe4BT, BT2BIP, BT2Fiacre). None of them takes a BT.CPP v3 XML file and produces a flattened action graph with a guard on every transition.

---

## 1. Comparison matrix

| Tool | Reads BT.CPP XML | Inlines subtrees and applies port remapping | Action-level success/failure graph | Guards on transitions | Formal verification | Open source |
|---|---|---|---|---|---|---|
| Groot 1 | yes (v3.8) | visual expand/collapse only | no | no | no | yes (MIT) |
| Groot2 | yes (v3 and v4, per vendor) | visual expand/collapse | no (none documented) | no (none documented) | no | no (freeware + paid PRO) |
| BT.CPP `VerifyXML` / XSD | yes | no (instantiates at runtime) | no | no | no | yes (MIT) |
| py_trees display / `py-trees-render` | no (Python trees) | n/a | no (draws tree structure) | no | no | yes (BSD) |
| py_trees XML parser (≥ 2.5.0) | BT.CPP-like XML, experimental | yes (namespaced keys) | no | no | no | yes (BSD) |
| Nav2 `tools/bt2img.py` | yes | no | no (draws tree structure) | no | no | yes (Apache-2.0) |
| VS Code extensions (Nav2 BT Editor, TreeSense) | yes | navigation only | no | no | no | not checked |
| BehaVerify | **no** (own `.tree` DSL) | n/a | no | implicit in the nuXmv model | LTL/CTL via nuXmv | yes (MIT) |
| BTCompiler (CARVE) | Groot-era XML | not documented | no | no | SMV models + Coq-verified interpreter | yes (BSD-2-Clause) |
| MoVe4BT | its own XML style | not checked | no | no | LTL over nodes | not checked |
| ArcadeBT | C++ BT encoding | n/a | no | no | safety via Horn clauses + Z3 | not checked |
| BT2BIP, BT2Fiacre | BT models (not BT.CPP XML, as far as found) | not checked | no | no | BIP / Fiacre + Tina | not checked |
| **Beehave (Phase 1)** | **yes (v3)** | **yes** | **yes** | **raw guards** | Phase 4 | yes |

---

## 2. Editors and monitors

### 2.1 Groot (1.x)

- **What it is:** a Qt graphical editor and runtime monitor for BT.CPP. Its README now carries a deprecation notice: "Groot 1.0 is compatible only with BehaviorTree.CPP 3.8.x", and the repository is in maintenance mode ([BehaviorTree/Groot README](https://github.com/BehaviorTree/Groot)). License: MIT (README "Licence" section, `package.xml`).
- **Subtrees:** each `SubTree` node has an **Expand/Collapse** button that inlines the subtree's body in the canvas ([`bt_editor/models/SubtreeNodeModel.cpp`](https://github.com/BehaviorTree/Groot/blob/master/bt_editor/models/SubtreeNodeModel.cpp), [`graphic_container.cpp`](https://github.com/BehaviorTree/Groot/blob/master/bt_editor/graphic_container.cpp)). This is purely visual. Port remapping values are shown as text, not resolved.
- **Validation:** it calls BT.CPP's `VerifyXML` with the palette of known models ([`XML_utilities.cpp`](https://github.com/BehaviorTree/Groot/blob/master/bt_editor/XML_utilities.cpp)).
- **Analysis:** there is no guard computation, no path enumeration and no action graph. Monitor mode shows live node statuses received over ZeroMQ from a running tree.
- **Caveat for us:** Groot 1 has no separate `SubTreePlus` model and writes every subtree as `<SubTree>`. See `btcpp-v3-xml.md` §5.4.

### 2.2 Groot2

- **What it is:** the official BT.CPP IDE, **closed source**, with a free edition and a paid "PRO" licence ([product page source](https://github.com/BehaviorTree/btcpp_website/blob/master/src/pages/groot.js)). Listed features include a drag-and-drop editor, multi-file projects (`.btproj`), split view, real-time XML preview, monitoring and log replay, and, in PRO, node search, blackboard visualisation, interactive breakpoints, fault injection and node substitution. The page states "Compatible with both BT.CPP 3 and 4".
- **Static checks:** according to the public changelog ([BehaviorTree/Groot2 README](https://github.com/BehaviorTree/Groot2)), 1.7.1 (2026-01-04) highlights wrong port names, and 1.8.0 (2026-01-18) added "Tree Hierarchy Analysis", which detects self-referencing subtrees and circular dependencies between trees.
- **Analysis:** nothing in the changelog or on the product page mentions guard computation, path or reachability analysis, or an action-level graph. Subtrees can be expanded in the editor. The tool itself was not run for this survey.

### 2.3 BT.CPP's own tooling

- `VerifyXML` checks the structure: arities for explicit tags and decorators, and that nodes are registered ([`src/xml_parsing.cpp` @ 3.8.8](https://github.com/BehaviorTree/BehaviorTree.CPP/blob/3.8.8/src/xml_parsing.cpp#L235-L437)).
- `writeTreeNodesModelXML` exports models for Groot. v4 adds `writeTreeXSD`, which generates an XSD for the registered nodes (master). The old static `behaviortree_schema.xsd`, still linked from the v3.8 docs, was **deleted in 2020** (commit `4107ac4`).
- `convert_v3_to_v4.py` is a partial XML converter. See `btcpp-v3-vs-v4.md` for its gaps.
- Loggers (file logger, ZeroMQ publisher, Groot2 publisher) record **runtime** traces only.

### 2.4 Editor plug-ins

- **Nav2 BT Editor**, a VS Code extension announced on ROS Discourse, edits and previews BehaviorTree.CPP and Nav2 XML as a graph. The announcement says it does not tick trees or replace runtime validation ([Discourse thread](https://discourse.openrobotics.org/t/nav2-bt-editor-a-vs-code-extension-for-editing-and-previewing-nav2-behavior-trees/55893)).
- **TreeSense** adds go-to-definition and hover previews for `<SubTree>` IDs ([Discourse thread](https://discourse.openrobotics.org/t/new-tool-for-working-with-behavior-trees/43369)).
- Both are known only from the search results summarising these announcements. Their versions, licences and exact features were **not checked**.

---

## 3. Renderers

### 3.1 py_trees

- **Display:** [`py_trees/display.py`](https://github.com/splintered-reality/py_trees/blob/devel/py_trees/display.py) provides `ascii_tree`, `unicode_tree`, `xhtml_tree`, `dot_tree` and `render_dot_tree`. The console script `py-trees-render` (`py_trees.programs.render:main`, declared in [`pyproject.toml`](https://github.com/splintered-reality/py_trees/blob/devel/pyproject.toml)) renders a tree returned by a Python function to dot, png or svg. The output is the **tree structure**, not an action graph.
- **XML parser (new):** py_trees 2.5.0 (2026-07-13) added input/output ports and an **experimental** parser for "the BehaviorTree XML format" ([`py_trees/parsers/behaviour_tree_xml.py`](https://github.com/splintered-reality/py_trees/blob/devel/py_trees/parsers/behaviour_tree_xml.py), [CHANGELOG](https://github.com/splintered-reality/py_trees/blob/devel/CHANGELOG.rst), PR #487). It instantiates `<SubTree>` templates and rewrites `{key}` references into absolute blackboard paths, one namespace per subtree instance (for example `/Subtree1/transfer_key`). This is very close to Beehave's Flatten step. Differences: it builds **executable** py_trees behaviours from a class registry, follows BT.CPP **v4-style** `{key}` subtree remapping, and only knows `sequence`, `selector`/`fallback`, `parallel` and py_trees decorators. It has no v3 classic `SubTree` or `SubTreePlus`/`__autoremap`, and no guard or action-graph output. Worth reading for its key-resolution algorithm. Licence: BSD.

### 3.2 Nav2

- **`bt_navigator`** loads BT.CPP XML at runtime. Humble uses BT.CPP v3, and the trees in [`nav2_bt_navigator/behavior_trees/`](https://github.com/ros-navigation/navigation2/tree/humble/nav2_bt_navigator/behavior_trees) have no subtrees. Jazzy uses v4 (`BTCPP_format="4"`).
- **`nav2_behavior_tree/nav2_tree_nodes.xml`** is a hand-maintained `<TreeNodesModel>` of all Nav2 plugin nodes, meant for Groot ([`groot_instructions.md`](https://github.com/ros-navigation/navigation2/blob/humble/nav2_behavior_tree/groot_instructions.md)). Jazzy also has `src/generate_nav2_tree_nodes_xml.cpp`, which generates it from the registered plugins. Beehave can use it directly as a model file. It is included as a fixture.
- **`tools/bt2img.py`** ([humble](https://github.com/ros-navigation/navigation2/blob/humble/tools/bt2img.py), Apache-2.0) converts a BT XML file to a Graphviz PNG. It uses **hard-coded lists** of control, action, condition and decorator names. Those lists are stale: for example, `SequenceStar` and `BlackboardCheck*` are listed as "control" nodes. It draws the parent/child tree only.
- **Groot usage docs:** [Nav2 "Groot Tutorials"](https://docs.nav2.org/tutorials/docs/using_groot.html).

---

## 4. Verification and formal-methods tools

### 4.1 BehaVerify

- Repository: [verivital/behaverify](https://github.com/verivital/behaverify) (MIT, commit `a9b768d`, 2026-08-26).
- **Input:** its own `.tree` DSL. The first version (SEFM 2022) took py_trees trees. The current source (`src/behaverify/`) has generators to nuXmv (`dsl_to_nuxmv.py`), Python/py_trees, Haskell, C++ (`dsl_to_cpp.py`, described as BT.CPP-compatible) and LaTeX. A search of the source found **no BT.CPP XML importer**.
- **Output and analysis:** nuXmv models for LTL and CTL checking, counter-examples, and runtime monitors (FMAS 2024).
- **Relevance:** it is the most mature open BT model checker and a candidate back end for Phase 4. Beehave could emit a BehaVerify `.tree` model from the flattened tree. Its encoding papers are listed in `literature.md`.

### 4.2 BTCompiler (CARVE project)

- Repository: [CARVE-ROBMOSYS/BTCompiler](https://github.com/CARVE-ROBMOSYS/BTCompiler) (BSD-2-Clause, last commit `2445120`, 2019-04-09). It is a **Coq-verified BT interpreter**, extracted to OCaml with a C interface (`readbt`, `tick`). It reads trees "as XML in Groot's format" ([RobMoSys wiki](https://robmosys.eu/wiki/baseline:environment_tools:carve-interpreter)). The example files in `groot/` use the old `<Root>` wrapper.
- The repository also contains hand-written and generated SMV models (`smv/bt_classic.smv`, `bt2spec.v`, `micro_smv.v`). The BehaVerify paper treats BTCompiler as the earlier LTL tool and notes that it does not support blackboard variables ([arXiv:2208.05360](https://arxiv.org/abs/2208.05360)).
- It is inactive and targets pre-v3 Groot XML. It does no remapping and draws no action graph.

### 4.3 MoVe4BT and ArcadeBT

- **MoVe4BT** ([move4bt.github.io](https://move4bt.github.io/), site not fetched): described by Serbinowska et al. as using "an xml style for specifying BTs", supporting LTL over **nodes** but not over variables, supporting true parallelism, and being GUI-only. The BehaVerify reproducibility notes say "we did not find a way to run the tool from the command-line" ([`REPRODUCIBILITY/2024_NFM/README.md`](https://github.com/verivital/behaverify/blob/main/REPRODUCIBILITY/2024_NFM/README.md)). The original paper and its authors were not identified with certainty.
- **ArcadeBT:** encodes a C++ BT implementation as linear constrained Horn clauses and checks safety properties with Z3 ("Formalizing Stateful Behavior Trees", [arXiv:2411.14165](https://arxiv.org/abs/2411.14165)). The original publication details were not verified.

### 4.4 BT2BIP and BT2Fiacre

- **BT2BIP:** Wang, Dai, Zhao, Zhang and Bliudze translate BTs into BIP components: each node becomes an extended automaton and each edge becomes interactions. The translation comes with a correctness proof and a prototype toolchain ([FACS 2024, LNCS 15189, DOI 10.1007/978-3-031-71261-6_1](https://doi.org/10.1007/978-3-031-71261-6_1)).
- **BT2Fiacre:** Ingrand gives BTs a formal semantics by translation to Fiacre, with Tina for model checking and Hippo as a runtime engine ([arXiv:2502.11904](https://arxiv.org/abs/2502.11904), [LAAS project](https://redmine.laas.fr/projects/bt2fiacre)).
- It was not checked whether either tool reads BT.CPP XML directly.

### 4.5 Event-B

Tadiello and Troubitsyna give a formal specification of BTs in Event-B and a method for proving invariants of existing trees ([arXiv:2209.14045](https://arxiv.org/abs/2209.14045)). This is a manual, proof-based approach, not a tool for XML.

---

## 5. BT ↔ FSM conversion

- No maintained, off-the-shelf **BT.CPP → state machine** converter was found.
- The closest automated translation is inside BehaVerify. "Formalizing Stateful Behavior Trees" translates stateful BTs with finite-type variables into a nondeterministic FSM, which feeds nuXmv ([arXiv:2411.14165](https://arxiv.org/abs/2411.14165)).
- The theory is covered in Colledanchise and Ögren (IEEE T-RO 2017; book chapter 6), in Biggar et al.'s expressiveness hierarchy and decision structures, and in the hand-made comparison by Iovino et al. ([arXiv:2405.16137](https://arxiv.org/abs/2405.16137)). See `literature.md`.
- **Name collision to avoid:** "Behavior Trees" is also the name of Dromey's *requirements* notation, which has its own BT → UML state machine translations (for example in the Journal of Systems and Software, 2012). Those papers are about a different formalism and do not apply to robotics BTs.

---

## 6. Data sets

- Ghzouli et al. mined open-source ROS projects for BT models, including BT.CPP XML, and **released a dataset** of real-world behaviour models (SLE 2020, [arXiv:2010.06256](https://arxiv.org/abs/2010.06256); IEEE TSE 2023, [arXiv:2208.04211](https://arxiv.org/abs/2208.04211)). This could be a large stress-test corpus for the parser. Licences differ per source project, so it cannot be vendored as is.

---

## 7. The gap Beehave fills

1. **XML-native and static.** Beehave reads BT.CPP v3 XML as written, together with `<TreeNodesModel>` and a small config. It needs no C++ build, no registered plugins and no robot.
2. **Faithful flattening.** It inlines `SubTree` and `SubTreePlus` with the exact v3.8 remapping rules (`__shared_blackboard`, `__autoremap`, literals, local keys). It detects recursion and include cycles. No surveyed tool resolves blackboard keys across subtree boundaries for BT.CPP v3. Groot only expands subtrees visually, and py_trees follows v4-style rules.
3. **Action graph instead of tree picture.** One box per action and one arrow per SUCCESS/FAILURE transition, labelled with the guard collected on the way. This is the view an operator or safety reviewer needs ("what can happen after `Land` fails?"). Every existing renderer draws the tree structure.
4. **Honest about semantics.** Reactive nodes, `Parallel`, memory (`SequenceStar`), timeouts and unknown custom controls are reported as **approximated**, not silently drawn as if they were exact.
5. **A bridge to formal methods.** The flattened tree and action graph give later phases one intermediate form for guard simplification (Phase 2), operator views (Phase 3) and export to model checkers such as BehaVerify or nuXmv (Phase 4). Today, each of those tools needs a hand-written model.
