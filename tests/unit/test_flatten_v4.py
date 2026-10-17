"""Flatten BT.CPP v4 subtrees: v4 remapping, port shorthands and scripts."""

from __future__ import annotations

from beehave.flatten import flatten
from beehave.model import Node, NodeKind
from beehave.parsers.btcpp_v4 import parse_string


def _doc(main_body: str, *subtrees: tuple[str, str]) -> str:
    trees = "".join(f'<BehaviorTree ID="{i}">{b}</BehaviorTree>' for i, b in subtrees)
    return (
        '<root BTCPP_format="4" main_tree_to_execute="Main">'
        f'<BehaviorTree ID="Main">{main_body}</BehaviorTree>{trees}</root>'
    )


def _leaves(xml: str) -> list[tuple[str, dict[str, str]]]:
    root = flatten(parse_string(xml)).root
    return [
        (n.type, dict(n.ports))
        for n in root.walk()
        if not n.children and n.kind is not NodeKind.SUBTREE
    ]


def _nodes(xml: str) -> list[Node]:
    return [n for n in flatten(parse_string(xml)).root.walk() if n.kind is not NodeKind.SUBTREE]


def test_remap_to_a_parent_key() -> None:
    xml = _doc('<SubTree ID="Go" target="{goal}"/>', ("Go", '<Move to="{target}"/>'))

    assert _leaves(xml) == [("Move", {"to": "{goal}"})]


def test_a_literal_is_local_to_the_instance() -> None:
    xml = _doc('<SubTree ID="Go" target="kitchen"/>', ("Go", '<Move to="{target}"/>'))

    assert _leaves(xml) == [("Move", {"to": "kitchen"})]


def test_unmapped_keys_are_private_without_autoremap() -> None:
    xml = _doc('<SubTree ID="Go"/>', ("Go", '<Move to="{target}"/>'))

    assert _leaves(xml) == [("Move", {"to": "{Go/target}"})]


def test_autoremap_forwards_every_key_but_private_ones() -> None:
    xml = _doc(
        '<SubTree ID="Go" _autoremap="true"/>',
        ("Go", '<Sequence><Move to="{target}"/><Log msg="{_scratch}"/></Sequence>'),
    )

    assert _leaves(xml) == [("Move", {"to": "{target}"}), ("Log", {"msg": "{Go/_scratch}"})]


def test_a_literal_after_autoremap_is_still_local() -> None:
    # The BT.CPP 3.8.4 quirk (the literal also written to the parent) is gone.
    xml = _doc(
        '<SubTree ID="Go" _autoremap="true" speed="0.5"/>',
        ("Go", '<Move speed="{speed}"/>'),
    )

    doc = flatten(parse_string(xml))

    assert _leaves(xml) == [("Move", {"speed": "0.5"})]
    assert doc.diagnostics == ()


def test_same_name_shorthand_on_a_subtree() -> None:
    xml = _doc('<SubTree ID="Go" goal="{=}"/>', ("Go", '<Move to="{goal}"/>'))

    assert _leaves(xml) == [("Move", {"to": "{goal}"})]


def test_same_name_shorthands_on_a_port() -> None:
    xml = _doc('<Sequence><Move goal="{=}"/><Turn angle="="/></Sequence>')

    assert _leaves(xml) == [("Move", {"goal": "{goal}"}), ("Turn", {"angle": "{angle}"})]


def test_root_blackboard_reference_from_any_depth() -> None:
    xml = _doc(
        '<SubTree ID="Outer"/>',
        ("Outer", '<SubTree ID="Inner"/>'),
        ("Inner", '<Report status="{@mission_status}"/>'),
    )

    assert _leaves(xml) == [("Report", {"status": "{mission_status}"})]


def test_root_reference_as_a_remap_value() -> None:
    xml = _doc(
        '<SubTree ID="Outer"/>',
        ("Outer", '<SubTree ID="Inner" status="{@mission_status}"/>'),
        ("Inner", '<Report status="{status}"/>'),
    )

    assert _leaves(xml) == [("Report", {"status": "{mission_status}"})]


def test_dollar_braces_are_a_literal_in_v4() -> None:
    xml = _doc('<SubTree ID="Go" target="${goal}"/>', ("Go", '<Move to="{target}"/>'))

    assert _leaves(xml) == [("Move", {"to": "${goal}"})]


def test_script_keys_are_remapped_too() -> None:
    xml = _doc(
        '<SubTree ID="Charge" level="{battery}" _skipIf="docked"/>',
        (
            "Charge",
            (
                '<Sequence><ScriptCondition code="level &lt; 20 &amp;&amp; !busy"/>'
                "<Script code=\"count := count + 1; label := 'level'\"/>"
                '<Plug _while="level &lt; 100"/></Sequence>'
            ),
        ),
    )

    nodes = _nodes(xml)

    condition, script, plug = (n for n in nodes if not n.children)
    assert condition.ports["code"] == "battery < 20 && !Charge/busy"
    assert script.ports["code"] == "Charge/count := Charge/count + 1; Charge/label := 'level'"
    assert dict(plug.scripts) == {"_while": "battery < 100"}


def test_conditions_on_a_subtree_read_the_parent_blackboard() -> None:
    xml = _doc(
        '<SubTree ID="Charge" docked="{at_dock}" _skipIf="docked"/>',
        ("Charge", "<Plug/>"),
    )

    reference = flatten(parse_string(xml)).root

    assert reference.kind is NodeKind.SUBTREE
    assert dict(reference.scripts) == {"_skipIf": "docked"}


def test_a_key_remapped_to_a_literal_becomes_that_value_in_scripts() -> None:
    xml = _doc(
        '<SubTree ID="Go" limit="20" mode="auto"/>',
        ("Go", "<ScriptCondition code=\"speed &lt; limit &amp;&amp; mode == 'auto'\"/>"),
    )

    (condition,) = _nodes(xml)

    assert condition.ports["code"] == "Go/speed < 20 && 'auto' == 'auto'"


def test_numbers_and_root_keys_in_scripts_are_left_alone() -> None:
    xml = _doc(
        '<SubTree ID="Go"/>',
        ("Go", '<Script code="mask := 0x7F; scale := 1e3; @total += 1"/>'),
    )

    (script,) = _nodes(xml)

    assert script.ports["code"] == "Go/mask := 0x7F; Go/scale := 1e3; total += 1"
