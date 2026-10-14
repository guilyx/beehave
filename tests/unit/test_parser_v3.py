"""BT.CPP v3 XML parser: XML in, format-agnostic tree model out."""

from __future__ import annotations

from pathlib import PureWindowsPath
from typing import TYPE_CHECKING

import pytest

from beehave.config import Config
from beehave.errors import ParseError, UnsupportedFormatError
from beehave.model import NodeKind, Semantics
from beehave.parsers import parse_file, parse_string
from beehave.parsers.btcpp_v3 import source_name
from tests.conftest import tree_xml

if TYPE_CHECKING:
    from pathlib import Path


def test_compact_syntax_builds_the_tree() -> None:
    doc = parse_string(tree_xml('<Sequence name="go"><Takeoff/><GoToZone zone="{z}"/></Sequence>'))

    root = doc.trees["Main"].root
    assert root.kind is NodeKind.CONTROL
    assert root.semantics is Semantics.SEQUENCE
    assert root.name == "go"
    assert [c.type for c in root.children] == ["Takeoff", "GoToZone"]
    assert root.children[1].ports == {"zone": "{z}"}


def test_custom_leaf_defaults_to_action() -> None:
    doc = parse_string(tree_xml("<Takeoff/>"))

    leaf = doc.trees["Main"].root
    assert leaf.kind is NodeKind.ACTION
    assert leaf.semantics is Semantics.CUSTOM


def test_explicit_syntax_uses_the_tag_as_kind() -> None:
    doc = parse_string(
        tree_xml(
            '<Sequence><Condition ID="BatteryOK" name="battery"/>'
            '<Action ID="Land" speed="1"/></Sequence>'
        )
    )

    cond, act = doc.trees["Main"].root.children
    assert (cond.kind, cond.type, cond.name) == (NodeKind.CONDITION, "BatteryOK", "battery")
    assert (act.kind, act.type, act.ports) == (NodeKind.ACTION, "Land", {"speed": "1"})


def test_tree_nodes_model_declares_conditions() -> None:
    xml = tree_xml(
        "<Sequence><IsEmergency/><Land/></Sequence>",
        extra='<TreeNodesModel><Condition ID="IsEmergency"/><Action ID="Land"/></TreeNodesModel>',
    )

    cond, act = parse_string(xml).trees["Main"].root.children
    assert cond.kind is NodeKind.CONDITION
    assert act.kind is NodeKind.ACTION


def test_config_overrides_everything_for_conditions_in_disguise() -> None:
    xml = tree_xml(
        '<Sequence><Action ID="BatteryOK"/><IsArmed/></Sequence>',
        extra='<TreeNodesModel><Action ID="IsArmed"/></TreeNodesModel>',
    )

    doc = parse_string(xml, config=Config(conditions=frozenset({"BatteryOK", "IsArmed"})))

    assert [c.kind for c in doc.trees["Main"].root.children] == [
        NodeKind.CONDITION,
        NodeKind.CONDITION,
    ]


def test_config_can_force_a_node_to_be_an_action() -> None:
    xml = tree_xml("<Probe/>", extra='<TreeNodesModel><Condition ID="Probe"/></TreeNodesModel>')

    doc = parse_string(xml, config=Config(actions=frozenset({"Probe"})))

    assert doc.trees["Main"].root.kind is NodeKind.ACTION


@pytest.mark.parametrize(
    ("xml_name", "semantics"),
    [
        ("Sequence", Semantics.SEQUENCE),
        ("SequenceStar", Semantics.SEQUENCE_WITH_MEMORY),
        ("ReactiveSequence", Semantics.REACTIVE_SEQUENCE),
        ("Fallback", Semantics.FALLBACK),
        ("ReactiveFallback", Semantics.REACTIVE_FALLBACK),
        ("Parallel", Semantics.PARALLEL),
    ],
)
def test_builtin_controls_map_to_one_internal_type(xml_name: str, semantics: Semantics) -> None:
    root = parse_string(tree_xml(f"<{xml_name}><A/><B/></{xml_name}>")).trees["Main"].root

    assert root.kind is NodeKind.CONTROL
    assert root.semantics is semantics
    assert root.type == xml_name


@pytest.mark.parametrize(
    ("xml_name", "semantics"),
    [
        ("Inverter", Semantics.INVERTER),
        ("ForceSuccess", Semantics.FORCE_SUCCESS),
        ("ForceFailure", Semantics.FORCE_FAILURE),
        ("RetryUntilSuccessful", Semantics.RETRY),
        ("Repeat", Semantics.REPEAT),
    ],
)
def test_builtin_decorators(xml_name: str, semantics: Semantics) -> None:
    root = parse_string(tree_xml(f"<{xml_name}><A/></{xml_name}>")).trees["Main"].root

    assert root.kind is NodeKind.DECORATOR
    assert root.semantics is semantics


def test_custom_node_with_one_child_is_a_decorator() -> None:
    root = parse_string(tree_xml("<Throttle><A/></Throttle>")).trees["Main"].root

    assert (root.kind, root.semantics) == (NodeKind.DECORATOR, Semantics.CUSTOM)


def test_custom_node_with_many_children_is_a_control() -> None:
    root = parse_string(tree_xml("<Vote><A/><B/></Vote>")).trees["Main"].root

    assert (root.kind, root.semantics) == (NodeKind.CONTROL, Semantics.CUSTOM)


def test_subtree_references_keep_the_target_and_remapping() -> None:
    xml = tree_xml(
        '<SubTreePlus ID="ReturnHome" __autoremap="true" zone="{home}"/>',
        extra='<BehaviorTree ID="ReturnHome"><Land/></BehaviorTree>',
    )

    ref = parse_string(xml).trees["Main"].root
    assert ref.kind is NodeKind.SUBTREE
    assert ref.semantics is Semantics.SUBTREE_PLUS
    assert ref.ref == "ReturnHome"
    assert ref.ports == {"__autoremap": "true", "zone": "{home}"}


def test_main_tree_is_read_from_the_root() -> None:
    xml = tree_xml("<A/>", extra='<BehaviorTree ID="Other"><B/></BehaviorTree>')

    doc = parse_string(xml)
    assert doc.main_tree == "Main"
    assert set(doc.trees) == {"Main", "Other"}


def test_single_tree_is_the_main_tree() -> None:
    assert parse_string(tree_xml("<A/>", main=None)).main_tree == "Main"


def test_many_trees_without_main_leave_it_unset() -> None:
    xml = tree_xml("<A/>", main=None, extra='<BehaviorTree ID="Other"><B/></BehaviorTree>')

    assert parse_string(xml).main_tree is None


def test_source_lines_are_recorded() -> None:
    xml = (
        '<root main_tree_to_execute="Main">\n'
        '<BehaviorTree ID="Main">\n'
        "  <Land/>\n"
        "</BehaviorTree>\n"
        "</root>"
    )

    land = parse_string(xml, source="mission.xml").trees["Main"].root
    assert land.location is not None
    assert (land.location.file, land.location.line) == ("mission.xml", 3)


def test_v4_format_is_detected_and_refused() -> None:
    xml = '<root BTCPP_format="4"><BehaviorTree ID="Main"><A/></BehaviorTree></root>'

    with pytest.raises(UnsupportedFormatError, match=r"BT\.CPP v4"):
        parse_string(xml)


def test_explicit_v3_marker_is_accepted() -> None:
    xml = '<root BTCPP_format="3"><BehaviorTree ID="Main"><A/></BehaviorTree></root>'

    assert parse_string(xml).format == "btcpp-v3"


@pytest.mark.parametrize(
    ("xml", "message"),
    [
        ("<root><BehaviorTree ID='Main'><A></root>", "not well-formed|mismatched tag"),
        ("<tree/>", "expected <root>"),
        ("<root/>", "no <BehaviorTree>"),
        ("<root><BehaviorTree><A/></BehaviorTree></root>", "missing the ID attribute"),
        ("<root><BehaviorTree ID='Main'/></root>", "exactly one child"),
        ("<root><BehaviorTree ID='Main'><A/><B/></BehaviorTree></root>", "exactly one child"),
        (
            "<root><BehaviorTree ID='M'><Inverter><A/><B/></Inverter></BehaviorTree></root>",
            "1 child",
        ),
        ("<root><BehaviorTree ID='M'><Inverter/></BehaviorTree></root>", "1 child"),
        ("<root><BehaviorTree ID='M'><Sequence/></BehaviorTree></root>", "at least 1 child"),
        ("<root><BehaviorTree ID='M'><Action><A/></Action></BehaviorTree></root>", "needs an ID"),
        ("<root><BehaviorTree ID='M'><SubTree/></BehaviorTree></root>", "needs an ID"),
        (
            "<root><BehaviorTree ID='M'><Condition ID='C'><A/></Condition></BehaviorTree></root>",
            "cannot have children",
        ),
        (
            "<root main_tree_to_execute='Nope'><BehaviorTree ID='M'><A/></BehaviorTree></root>",
            "'Nope' is not defined",
        ),
    ],
)
def test_malformed_documents_raise_parse_errors(xml: str, message: str) -> None:
    with pytest.raises(ParseError, match=message):
        parse_string(xml)


def test_parse_errors_carry_the_location() -> None:
    xml = "<root>\n<BehaviorTree ID='M'>\n<Inverter/>\n</BehaviorTree></root>"

    with pytest.raises(ParseError) as info:
        parse_string(xml, source="bad.xml")
    assert "bad.xml:3" in str(info.value)


def test_doctype_is_rejected() -> None:
    xml = '<!DOCTYPE root [<!ENTITY x "y">]><root><BehaviorTree ID="M"><A/></BehaviorTree></root>'

    with pytest.raises(ParseError, match="DOCTYPE"):
        parse_string(xml)


def test_parse_file_follows_includes(tmp_path: Path) -> None:
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "home.xml").write_text(
        '<root><BehaviorTree ID="ReturnHome"><Land/></BehaviorTree>'
        '<TreeNodesModel><Condition ID="AtHome"/></TreeNodesModel></root>'
    )
    (tmp_path / "main.xml").write_text(
        '<root main_tree_to_execute="Main"><include path="sub/home.xml"/>'
        '<BehaviorTree ID="Main"><Sequence><AtHome/><SubTree ID="ReturnHome"/></Sequence>'
        "</BehaviorTree></root>"
    )

    doc = parse_file(tmp_path / "main.xml")

    assert set(doc.trees) == {"Main", "ReturnHome"}
    assert doc.trees["Main"].root.children[0].kind is NodeKind.CONDITION
    assert doc.trees["ReturnHome"].location is not None
    assert doc.trees["ReturnHome"].location.file == (tmp_path / "sub" / "home.xml").as_posix()


def test_include_cycles_are_loaded_once(tmp_path: Path) -> None:
    (tmp_path / "a.xml").write_text(
        '<root main_tree_to_execute="A"><include path="b.xml"/>'
        '<BehaviorTree ID="A"><SubTree ID="B"/></BehaviorTree></root>'
    )
    (tmp_path / "b.xml").write_text(
        '<root><include path="a.xml"/><BehaviorTree ID="B"><X/></BehaviorTree></root>'
    )

    assert set(parse_file(tmp_path / "a.xml").trees) == {"A", "B"}


def test_missing_include_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "a.xml").write_text(
        '<root><include path="nope.xml"/><BehaviorTree ID="A"><X/></BehaviorTree></root>'
    )

    with pytest.raises(ParseError, match=r"nope\.xml"):
        parse_file(tmp_path / "a.xml")


def test_ros_package_includes_are_reported_not_followed() -> None:
    xml = (
        '<root><include ros_pkg="my_pkg" path="t.xml"/>'
        '<BehaviorTree ID="A"><X/></BehaviorTree></root>'
    )

    doc = parse_string(xml)

    assert [d.code for d in doc.diagnostics] == ["unresolved-include"]


def test_parse_file_reads_several_files(tmp_path: Path) -> None:
    (tmp_path / "a.xml").write_text('<root><BehaviorTree ID="A"><X/></BehaviorTree></root>')
    (tmp_path / "b.xml").write_text('<root><BehaviorTree ID="B"><Y/></BehaviorTree></root>')

    doc = parse_file(tmp_path / "a.xml", tmp_path / "b.xml")

    assert set(doc.trees) == {"A", "B"}
    assert doc.main_tree is None


# ------------------------------------------------ details from BT.CPP 3.8.8 ---


def test_while_do_else_needs_exactly_three_children_in_v3() -> None:
    with pytest.raises(ParseError, match="exactly 3 children"):
        parse_string(tree_xml("<WhileDoElse><A/><B/></WhileDoElse>"))


def test_blackboard_check_bool_is_a_builtin() -> None:
    root = (
        parse_string(tree_xml("<BlackboardCheckBool><A/></BlackboardCheckBool>")).trees["Main"].root
    )

    assert root.semantics is Semantics.BLACKBOARD_CHECK


def test_duplicate_trees_keep_the_first_and_warn() -> None:
    xml = (
        "<root><BehaviorTree ID='M'><A/></BehaviorTree>"
        "<BehaviorTree ID='M'><B/></BehaviorTree></root>"
    )

    doc = parse_string(xml)

    assert doc.trees["M"].root.type == "A"
    assert [d.code for d in doc.diagnostics] == ["duplicate-tree"]


def test_included_trees_shadow_local_ones_like_bt_cpp(tmp_path: Path) -> None:
    (tmp_path / "inc.xml").write_text(
        '<root><BehaviorTree ID="T"><FromInclude/></BehaviorTree></root>'
    )
    (tmp_path / "main.xml").write_text(
        '<root main_tree_to_execute="T"><BehaviorTree ID="T"><Local/></BehaviorTree>'
        '<include path="inc.xml"/></root>'
    )

    assert parse_file(tmp_path / "main.xml").trees["T"].root.type == "FromInclude"


def test_main_tree_comes_from_the_first_file_that_names_one(tmp_path: Path) -> None:
    (tmp_path / "models.xml").write_text(
        '<root><TreeNodesModel><Condition ID="Ok"/></TreeNodesModel></root>'
    )
    (tmp_path / "tree.xml").write_text(
        '<root main_tree_to_execute="A"><BehaviorTree ID="A"><Ok/></BehaviorTree>'
        '<BehaviorTree ID="B"><X/></BehaviorTree></root>'
    )

    doc = parse_file(tmp_path / "models.xml", tmp_path / "tree.xml")

    assert doc.main_tree == "A"
    assert doc.trees["A"].root.kind is NodeKind.CONDITION


@pytest.mark.parametrize(
    ("body", "evidence"),
    [
        ("<SequenceWithMemory><A/></SequenceWithMemory>", "<SequenceWithMemory>"),
        ('<Script code="x:=1"/>', "<Script>"),
        ('<A _skipIf="x"/>', "_skipIf"),
        ('<SubTree ID="S" _autoremap="true"/>', "_autoremap"),
        ('<A value="{=}"/>', "{=}"),
        ('<A value="{@root_key}"/>', "{@root_key}"),
        ('<Parallel success_count="1"><A/><B/></Parallel>', "success_count"),
    ],
)
def test_v4_files_without_a_marker_are_detected(body: str, evidence: str) -> None:
    with pytest.raises(UnsupportedFormatError, match=r"looks like BT\.CPP v4") as info:
        parse_string(tree_xml(body), source="t.xml")
    assert evidence in str(info.value)
    assert "t.xml:1" in str(info.value)


def test_a_declared_custom_node_with_a_v4_name_is_not_evidence() -> None:
    xml = tree_xml("<Sleep/>", extra='<TreeNodesModel><Action ID="Sleep"/></TreeNodesModel>')

    assert parse_string(xml).trees["Main"].root.type == "Sleep"


def test_unknown_format_marker_is_a_warning() -> None:
    doc = parse_string('<root BTCPP_format="5"><BehaviorTree ID="M"><A/></BehaviorTree></root>')

    assert [d.code for d in doc.diagnostics] == ["unknown-format-marker"]


def test_compact_subtree_reference_is_accepted_with_a_warning() -> None:
    xml = tree_xml(
        "<Sequence><Talk/></Sequence>", extra='<BehaviorTree ID="Talk"><Say/></BehaviorTree>'
    )

    doc = parse_string(xml)

    ref = doc.trees["Main"].root.children[0]
    assert (ref.kind, ref.semantics, ref.ref) == (NodeKind.SUBTREE, Semantics.SUBTREE, "Talk")
    assert [d.code for d in doc.diagnostics] == ["compact-subtree-reference"]


def test_source_paths_use_forward_slashes_on_every_os() -> None:
    assert source_name(PureWindowsPath("nav2\\trees\\follow.xml")) == "nav2/trees/follow.xml"
