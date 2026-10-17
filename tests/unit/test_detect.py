"""Format detection: which BT.CPP version a set of files is written in."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from beehave.config import Config
from beehave.errors import ParseError
from beehave.parsers import detect_version
from tests.conftest import FIXTURES

if TYPE_CHECKING:
    from pathlib import Path

PUBLIC = FIXTURES / "public"


def _write(tmp_path: Path, name: str, xml: str) -> Path:
    path = tmp_path / name
    path.write_text(xml)
    return path


def test_v3_marker(tmp_path: Path) -> None:
    path = _write(
        tmp_path, "t.xml", '<root BTCPP_format="3"><BehaviorTree ID="T"><A/></BehaviorTree></root>'
    )

    assert detect_version(path) == "3"


def test_v4_marker(tmp_path: Path) -> None:
    path = _write(
        tmp_path, "t.xml", '<root BTCPP_format="4"><BehaviorTree ID="T"><A/></BehaviorTree></root>'
    )

    assert detect_version(path) == "4"


def test_no_marker_and_no_evidence_defaults_to_v3(tmp_path: Path) -> None:
    path = _write(tmp_path, "t.xml", '<root><BehaviorTree ID="T"><A/></BehaviorTree></root>')

    assert detect_version(path) == "3"


def test_v4_evidence_without_a_marker(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "t.xml",
        '<root><BehaviorTree ID="T">'
        "<SequenceWithMemory><A/></SequenceWithMemory>"
        "</BehaviorTree></root>",
    )

    assert detect_version(path) == "4"


def test_declared_node_with_a_v4_name_is_not_evidence(tmp_path: Path) -> None:
    path = _write(
        tmp_path,
        "t.xml",
        '<root><BehaviorTree ID="T"><Sleep/></BehaviorTree>'
        '<TreeNodesModel><Action ID="Sleep"/></TreeNodesModel></root>',
    )

    assert detect_version(path) == "3"
    assert detect_version(path, config=Config(actions=frozenset({"Sleep"}))) == "3"


def test_a_models_only_file_takes_the_version_of_the_trees(tmp_path: Path) -> None:
    models = _write(
        tmp_path, "m.xml", '<root><TreeNodesModel><Condition ID="Ok"/></TreeNodesModel></root>'
    )
    tree = _write(
        tmp_path, "t.xml", '<root BTCPP_format="4"><BehaviorTree ID="T"><Ok/></BehaviorTree></root>'
    )

    assert detect_version(models, tree) == "4"


def test_mixing_versions_is_an_error(tmp_path: Path) -> None:
    v3 = _write(
        tmp_path, "a.xml", '<root BTCPP_format="3"><BehaviorTree ID="A"><X/></BehaviorTree></root>'
    )
    v4 = _write(
        tmp_path, "b.xml", '<root BTCPP_format="4"><BehaviorTree ID="B"><Y/></BehaviorTree></root>'
    )

    with pytest.raises(ParseError, match=r"mix BT\.CPP v3 .* and v4"):
        detect_version(v3, v4)


@pytest.mark.parametrize(
    ("relative", "version"),
    [
        ("btcpp-v3/examples/test_files/subtree_test.xml", "3"),
        ("nav2/nav2_bt_navigator/behavior_trees/follow_point.xml", "3"),
        ("v4/btcpp/examples/test_files/Check.xml", "4"),
        ("v4/btcpp/examples/test_files/log_test.xml", "4"),
    ],
)
def test_public_trees(relative: str, version: str) -> None:
    assert detect_version(PUBLIC / relative) == version
