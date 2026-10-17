"""BT.CPP v4 XML parser, and the version detection in front of both parsers."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beehave.config import Config
from beehave.errors import ParseError, UnsupportedFormatError
from beehave.model import Node, NodeKind, Semantics
from beehave.parsers import parse_file, parse_string
from beehave.parsers.btcpp_v4 import parse_string as parse_v4

if TYPE_CHECKING:
    from pathlib import Path


def v4(body: str, *, extra: str = "", main: str | None = "Main") -> str:
    main_attr = f' main_tree_to_execute="{main}"' if main else ""
    return (
        f'<root BTCPP_format="4"{main_attr}><BehaviorTree ID="Main">{body}</BehaviorTree>'
        f"{extra}</root>"
    )


def root(body: str, **kwargs: str) -> Node:
    return parse_v4(v4(body, **kwargs)).trees["Main"].root


# --------------------------------------------------------------- built-ins ---


@pytest.mark.parametrize(
    ("body", "kind", "semantics"),
    [
        ("<Sequence><A/></Sequence>", NodeKind.CONTROL, Semantics.SEQUENCE),
        ("<AsyncSequence><A/></AsyncSequence>", NodeKind.CONTROL, Semantics.SEQUENCE),
        (
            "<SequenceWithMemory><A/></SequenceWithMemory>",
            NodeKind.CONTROL,
            Semantics.SEQUENCE_WITH_MEMORY,
        ),
        (
            "<ReactiveSequence><A/></ReactiveSequence>",
            NodeKind.CONTROL,
            Semantics.REACTIVE_SEQUENCE,
        ),
        ("<Fallback><A/></Fallback>", NodeKind.CONTROL, Semantics.FALLBACK),
        ("<AsyncFallback><A/></AsyncFallback>", NodeKind.CONTROL, Semantics.FALLBACK),
        (
            "<ReactiveFallback><A/></ReactiveFallback>",
            NodeKind.CONTROL,
            Semantics.REACTIVE_FALLBACK,
        ),
        ("<Parallel><A/><B/></Parallel>", NodeKind.CONTROL, Semantics.PARALLEL),
        ("<ParallelAll><A/><B/></ParallelAll>", NodeKind.CONTROL, Semantics.PARALLEL_ALL),
        ("<IfThenElse><C/><A/></IfThenElse>", NodeKind.CONTROL, Semantics.IF_THEN_ELSE),
        ("<WhileDoElse><C/><A/></WhileDoElse>", NodeKind.CONTROL, Semantics.WHILE_DO_ELSE),
        ("<TryCatch><A/><B/></TryCatch>", NodeKind.CONTROL, Semantics.TRY_CATCH),
        ('<Switch2 variable="{v}"><A/><B/><C/></Switch2>', NodeKind.CONTROL, Semantics.SWITCH),
        ("<Inverter><A/></Inverter>", NodeKind.DECORATOR, Semantics.INVERTER),
        ("<ForceSuccess><A/></ForceSuccess>", NodeKind.DECORATOR, Semantics.FORCE_SUCCESS),
        ("<ForceFailure><A/></ForceFailure>", NodeKind.DECORATOR, Semantics.FORCE_FAILURE),
        ('<Repeat num_cycles="2"><A/></Repeat>', NodeKind.DECORATOR, Semantics.REPEAT),
        (
            '<RetryUntilSuccessful num_attempts="2"><A/></RetryUntilSuccessful>',
            NodeKind.DECORATOR,
            Semantics.RETRY,
        ),
        (
            "<KeepRunningUntilFailure><A/></KeepRunningUntilFailure>",
            NodeKind.DECORATOR,
            Semantics.KEEP_RUNNING_UNTIL_FAILURE,
        ),
        ('<Timeout msec="10"><A/></Timeout>', NodeKind.DECORATOR, Semantics.TIMEOUT),
        ('<Delay delay_msec="10"><A/></Delay>', NodeKind.DECORATOR, Semantics.DELAY),
        ("<RunOnce><A/></RunOnce>", NodeKind.DECORATOR, Semantics.RUN_ONCE),
        ('<Precondition if="x"><A/></Precondition>', NodeKind.DECORATOR, Semantics.PRECONDITION),
        ('<LoopInt queue="1;2"><A/></LoopInt>', NodeKind.DECORATOR, Semantics.LOOP_QUEUE),
        ('<LoopString queue="a"><A/></LoopString>', NodeKind.DECORATOR, Semantics.LOOP_QUEUE),
        (
            '<SkipUnlessUpdated entry="{k}"><A/></SkipUnlessUpdated>',
            NodeKind.DECORATOR,
            Semantics.SKIP_UNLESS_UPDATED,
        ),
        (
            '<WaitValueUpdate entry="{k}"><A/></WaitValueUpdate>',
            NodeKind.DECORATOR,
            Semantics.DELAY,
        ),
        ("<AlwaysSuccess/>", NodeKind.ACTION, Semantics.ALWAYS_SUCCESS),
        ("<AlwaysFailure/>", NodeKind.ACTION, Semantics.ALWAYS_FAILURE),
        ('<SetBlackboard value="1" output_key="k"/>', NodeKind.ACTION, Semantics.SET_BLACKBOARD),
        ('<UnsetBlackboard key="k"/>', NodeKind.ACTION, Semantics.SET_BLACKBOARD),
        ('<Script code="x := 1"/>', NodeKind.ACTION, Semantics.SCRIPT),
        ('<Sleep msec="100"/>', NodeKind.ACTION, Semantics.WAIT),
        ('<ScriptCondition code="x &gt; 1"/>', NodeKind.CONDITION, Semantics.SCRIPT_CONDITION),
        ('<WasEntryUpdated entry="{k}"/>', NodeKind.CONDITION, Semantics.ENTRY_UPDATED),
    ],
    ids=lambda v: v.split(" ")[0].split(">")[0].lstrip("<") if isinstance(v, str) else None,
)
def test_builtins(body: str, kind: NodeKind, semantics: Semantics) -> None:
    extra = '<TreeNodesModel><Condition ID="C"/></TreeNodesModel>'

    node = parse_v4(v4(body, extra=extra)).trees["Main"].root

    assert (node.kind, node.semantics) == (kind, semantics)


def test_document_format() -> None:
    assert parse_v4(v4("<A/>")).format == "btcpp-v4"


def test_explicit_form_and_models_work_as_in_v3() -> None:
    doc = parse_v4(
        v4(
            '<Sequence><Condition ID="IsReady"/><Busy/></Sequence>',
            extra='<TreeNodesModel><Condition ID="Busy"/></TreeNodesModel>',
        )
    )

    kinds = [c.kind for c in doc.trees["Main"].root.children]
    assert kinds == [NodeKind.CONDITION, NodeKind.CONDITION]


# ------------------------------------------------- scripts and attributes ---


def test_pre_and_post_conditions_are_scripts_not_ports() -> None:
    node = root('<Charge level="{l}" _skipIf="battery &gt; 80" _onSuccess="charged := true"/>')

    assert dict(node.ports) == {"level": "{l}"}
    assert dict(node.scripts) == {"_skipIf": "battery > 80", "_onSuccess": "charged := true"}


def test_other_underscore_attributes_are_ignored() -> None:
    node = root('<Charge _description="top up" _uid="7" level="1"/>')

    assert dict(node.ports) == {"level": "1"}
    assert dict(node.scripts) == {}


def test_subtree_keeps_autoremap_and_takes_conditions() -> None:
    doc = parse_v4(
        v4(
            '<SubTree ID="Dock" _autoremap="true" goal="{dock}" _skipIf="docked"/>',
            extra='<BehaviorTree ID="Dock"><DockRobot/></BehaviorTree>',
        )
    )

    ref = doc.trees["Main"].root
    assert (ref.kind, ref.semantics, ref.ref) == (
        NodeKind.SUBTREE,
        Semantics.SUBTREE_V4,
        "Dock",
    )
    assert dict(ref.ports) == {"_autoremap": "true", "goal": "{dock}"}
    assert dict(ref.scripts) == {"_skipIf": "docked"}


# ---------------------------------------------------------------- structure ---


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("<TryCatch><A/></TryCatch>", "<TryCatch> needs at least 2 children, found 1"),
        (
            "<IfThenElse><C/><A/><B/><D/></IfThenElse>",
            "<IfThenElse> needs 2 to 3 children, found 4",
        ),
        ("<WhileDoElse><C/></WhileDoElse>", "<WhileDoElse> needs 2 to 3 children, found 1"),
        (
            '<Switch2 variable="{v}"><A/><B/></Switch2>',
            "<Switch2> needs exactly 3 children, found 2",
        ),
        ("<ForceSuccess/>", "<ForceSuccess> needs exactly 1 child, found 0"),
    ],
)
def test_child_counts_are_checked(body: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_v4(v4(body))


@pytest.mark.parametrize("tag", ["SubTreePlus", "BlackboardCheckInt", "ManualSelector"])
def test_v3_only_nodes_are_refused(tag: str) -> None:
    with pytest.raises(ParseError, match=rf"<{tag}> does not exist in BT\.CPP v4"):
        parse_v4(v4(f'<{tag} ID="X" value_A="1" value_B="1"><A/></{tag}>'))


def test_a_declared_node_with_a_v3_name_is_a_user_node() -> None:
    node = root(
        "<ManualSelector><A/><B/></ManualSelector>",
        extra='<TreeNodesModel><Control ID="ManualSelector"/></TreeNodesModel>',
    )

    assert (node.kind, node.semantics) == (NodeKind.CONTROL, Semantics.CUSTOM)


def test_sequence_star_is_read_with_a_warning() -> None:
    doc = parse_v4(v4("<SequenceStar><A/></SequenceStar>"))

    assert doc.trees["Main"].root.semantics is Semantics.SEQUENCE_WITH_MEMORY
    assert [d.code for d in doc.diagnostics] == ["v3-name"]


def test_the_last_definition_of_a_tree_wins() -> None:
    xml = (
        '<root BTCPP_format="4" main_tree_to_execute="T">'
        '<BehaviorTree ID="T"><First/></BehaviorTree>'
        '<BehaviorTree ID="T"><Second/></BehaviorTree></root>'
    )

    doc = parse_v4(xml)

    assert doc.trees["T"].root.type == "Second"
    assert [d.code for d in doc.diagnostics] == ["duplicate-tree"]
    assert "the last definition is used" in doc.diagnostics[0].message


def test_main_tree_is_the_only_tree_of_the_top_level_file(tmp_path: Path) -> None:
    (tmp_path / "lib.xml").write_text(
        '<root BTCPP_format="4"><BehaviorTree ID="Lib"><L/></BehaviorTree></root>',
        encoding="utf-8",
    )
    (tmp_path / "main.xml").write_text(
        '<root BTCPP_format="4"><include path="lib.xml"/>'
        '<BehaviorTree ID="App"><SubTree ID="Lib"/></BehaviorTree></root>',
        encoding="utf-8",
    )

    assert parse_file(tmp_path / "main.xml").main_tree == "App"


# ------------------------------------------------------- version detection ---


def test_parse_string_reads_both_versions() -> None:
    v3 = '<root main_tree_to_execute="M"><BehaviorTree ID="M"><A/></BehaviorTree></root>'

    assert parse_string(v3).format == "btcpp-v3"
    assert parse_string(v4("<A/>")).format == "btcpp-v4"


def test_parse_string_detects_v4_without_a_marker() -> None:
    xml = '<root><BehaviorTree ID="M"><A _skipIf="x"/></BehaviorTree></root>'

    assert parse_string(xml).format == "btcpp-v4"


def test_parse_file_reads_v4(tmp_path: Path) -> None:
    path = tmp_path / "t.xml"
    path.write_text(v4("<A/>"), encoding="utf-8")

    assert parse_file(path).format == "btcpp-v4"


def test_v4_parser_refuses_a_v3_marker() -> None:
    xml = '<root BTCPP_format="3"><BehaviorTree ID="M"><A/></BehaviorTree></root>'

    with pytest.raises(UnsupportedFormatError, match=r"BT\.CPP v3"):
        parse_v4(xml)


def test_config_is_used_by_detection_and_parsing() -> None:
    xml = '<root><BehaviorTree ID="M"><Sequence><Sleep/><Ready/></Sequence></BehaviorTree></root>'
    config = Config(actions=frozenset({"Sleep"}), conditions=frozenset({"Ready"}))

    doc = parse_string(xml, config=config)

    assert doc.format == "btcpp-v3"
    assert [c.kind for c in doc.trees["M"].root.children] == [NodeKind.ACTION, NodeKind.CONDITION]


@pytest.mark.parametrize(
    ("body", "evidence"),
    [
        ('<Sequence memory="true"><A/></Sequence>', "memory= on <Sequence>"),
        ('<Parallel policy="success_on_all"><A/></Parallel>', "policy= on <Parallel>"),
    ],
)
def test_py_trees_xml_is_refused_with_a_pointer(body: str, evidence: str) -> None:
    xml = f'<root main_tree_to_execute="M"><BehaviorTree ID="M">{body}</BehaviorTree></root>'

    with pytest.raises(UnsupportedFormatError, match="looks like py_trees XML") as info:
        parse_string(xml)
    assert evidence in str(info.value)
    assert "--py-trees" in str(info.value)
