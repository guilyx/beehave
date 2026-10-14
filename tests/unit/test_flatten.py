"""Flatten: inline every subtree, applying BT.CPP port remapping."""

from __future__ import annotations

import pytest

from beehave.errors import FlattenError, TreeSelectionError
from beehave.flatten import flatten
from beehave.model import Node, NodeKind
from beehave.parsers import parse_string


def _doc(main_body: str, *subtrees: tuple[str, str], main: str | None = "Main") -> str:
    main_attr = f' main_tree_to_execute="{main}"' if main else ""
    trees = "".join(f'<BehaviorTree ID="{i}">{b}</BehaviorTree>' for i, b in subtrees)
    return f'<root{main_attr}><BehaviorTree ID="Main">{main_body}</BehaviorTree>{trees}</root>'


def _leaves(node: Node) -> list[tuple[str, dict[str, str]]]:
    return [
        (n.type, dict(n.ports))
        for n in node.walk()
        if not n.children and n.kind is not NodeKind.SUBTREE
    ]


def test_tree_without_subtrees_is_unchanged() -> None:
    doc = parse_string(_doc('<Sequence><A x="{k}"/><B/></Sequence>'))

    assert flatten(doc).root == doc.trees["Main"].root


def test_subtree_body_is_inlined_under_the_reference() -> None:
    doc = parse_string(_doc('<SubTreePlus ID="Home" __autoremap="true"/>', ("Home", "<Land/>")))

    flat = flatten(doc)

    assert flat.root.kind is NodeKind.SUBTREE
    assert flat.root.ref == "Home"
    assert [c.type for c in flat.root.children] == ["Land"]


def test_autoremap_keeps_key_names() -> None:
    doc = parse_string(
        _doc('<SubTreePlus ID="Home" __autoremap="true"/>', ("Home", '<Fly zone="{zone}"/>'))
    )

    assert _leaves(flatten(doc).root) == [("Fly", {"zone": "{zone}"})]


def test_explicit_remap_points_to_the_outer_key() -> None:
    doc = parse_string(
        _doc('<SubTreePlus ID="Home" zone="{home_zone}"/>', ("Home", '<Fly zone="{zone}"/>'))
    )

    assert _leaves(flatten(doc).root) == [("Fly", {"zone": "{home_zone}"})]


def test_explicit_remap_wins_over_autoremap() -> None:
    doc = parse_string(
        _doc(
            '<SubTreePlus ID="Home" __autoremap="1" zone="{home}"/>',
            ("Home", '<Fly zone="{zone}" speed="{speed}"/>'),
        )
    )

    assert _leaves(flatten(doc).root) == [("Fly", {"zone": "{home}", "speed": "{speed}"})]


def test_literal_remap_replaces_the_reference_with_the_value() -> None:
    doc = parse_string(_doc('<SubTreePlus ID="Home" zone="3"/>', ("Home", '<Fly zone="{zone}"/>')))

    assert _leaves(flatten(doc).root) == [("Fly", {"zone": "3"})]


def test_unmapped_keys_are_private_to_the_subtree_instance() -> None:
    doc = parse_string(
        _doc(
            '<Sequence><SubTreePlus ID="Home"/><SubTreePlus ID="Home"/></Sequence>',
            ("Home", '<Fly zone="{zone}"/>'),
        )
    )

    assert _leaves(flatten(doc).root) == [
        ("Fly", {"zone": "{Home/zone}"}),
        ("Fly", {"zone": "{Home#2/zone}"}),
    ]


def test_v3_subtree_remaps_bare_key_names() -> None:
    doc = parse_string(
        _doc('<SubTree ID="Move" target="move_goal"/>', ("Move", '<MoveBase goal="{target}"/>'))
    )

    assert _leaves(flatten(doc).root) == [("MoveBase", {"goal": "{move_goal}"})]


def test_v3_subtree_shared_blackboard_keeps_key_names() -> None:
    doc = parse_string(
        _doc(
            '<SubTree ID="Move" __shared_blackboard="true"/>',
            ("Move", '<MoveBase goal="{target}"/>'),
        )
    )

    assert _leaves(flatten(doc).root) == [("MoveBase", {"goal": "{target}"})]


def test_nested_remaps_resolve_through_every_level() -> None:
    doc = parse_string(
        _doc(
            '<SubTreePlus ID="Home" zone="{home}"/>',
            ("Home", '<SubTreePlus ID="Approach" target="{zone}" alt="{alt}"/>'),
            ("Approach", '<Fly to="{target}" alt="{alt}" speed="2"/>'),
        )
    )

    assert _leaves(flatten(doc).root) == [
        ("Fly", {"to": "{home}", "alt": "{Home/alt}", "speed": "2"}),
    ]


def test_literals_and_non_reference_values_are_left_alone() -> None:
    doc = parse_string(
        _doc('<SubTreePlus ID="Home"/>', ("Home", '<Say msg="{not a key" other="x}"/>'))
    )

    assert _leaves(flatten(doc).root) == [("Say", {"msg": "{not a key", "other": "x}"})]


def test_missing_subtree_is_an_error_with_location() -> None:
    doc = parse_string(_doc('<SubTree ID="Nope"/>'), source="m.xml")

    with pytest.raises(FlattenError, match="'Nope' is not defined") as info:
        flatten(doc)
    assert "m.xml:1" in str(info.value)


def test_recursive_subtree_is_an_error() -> None:
    doc = parse_string(
        _doc(
            '<SubTree ID="A"/>',
            ("A", '<Sequence><X/><SubTree ID="B"/></Sequence>'),
            ("B", '<SubTree ID="A"/>'),
        )
    )

    with pytest.raises(FlattenError, match="recursive subtree: Main -> A -> B -> A"):
        flatten(doc)


def test_explicit_tree_selection() -> None:
    doc = parse_string(_doc("<A/>", ("Other", "<B/>")))

    assert flatten(doc, "Other").root.type == "B"
    assert flatten(doc, "Other").id == "Other"


def test_no_main_tree_requires_a_selection() -> None:
    doc = parse_string(_doc("<A/>", ("Other", "<B/>"), main=None))

    with pytest.raises(TreeSelectionError, match="Main, Other"):
        flatten(doc)


def test_unknown_tree_selection_is_an_error() -> None:
    doc = parse_string(_doc("<A/>"))

    with pytest.raises(TreeSelectionError, match="'Nope'"):
        flatten(doc, "Nope")
