"""Graph diff: what changed between the action graphs of two trees (QM4)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

import beehave
from beehave.cli import main
from beehave.config import Config
from beehave.diff import GraphDiff, TransitionScore, VertexKey, diff_graphs
from beehave.flatten import flatten
from beehave.parsers import parse_string
from beehave.walk import build_graph
from tests.conftest import EXAMPLES

if TYPE_CHECKING:
    from pathlib import Path

    from beehave.graph import ActionGraph

CONFIG = Config(conditions=frozenset({"IsReady", "IsClear"}))

OLD = """
<Sequence>
  <IsReady/>
  <Arm/>
  <TakeOff altitude="10"/>
  <Fallback name="work">
    <Survey/>
    <ReturnHome/>
  </Fallback>
</Sequence>
"""


def graph(body: str) -> ActionGraph:
    xml = f'<root><BehaviorTree ID="Mission">{body}</BehaviorTree></root>'
    return build_graph(flatten(parse_string(xml, config=CONFIG)))


def diff(old: str, new: str) -> GraphDiff:
    return diff_graphs(graph(old), graph(new))


def action(path: str) -> VertexKey:
    return VertexKey(path=path)


def test_a_graph_has_no_diff_with_itself() -> None:
    result = diff(OLD, OLD)

    assert not result.changed
    assert result.to_text() == "no change\n"
    assert result.score == TransitionScore(matched=10, old=10, new=10)
    assert (result.score.precision, result.score.recall, result.score.f1) == (1.0, 1.0, 1.0)


def test_actions_are_matched_by_path_not_by_display_id() -> None:
    # One action added at the top shifts every display ID and runtime id.
    result = diff(OLD, OLD.replace("<IsReady/>", "<IsReady/><Calibrate/>"))

    assert result.added_actions == (action("Sequence/Calibrate"),)
    assert result.removed_actions == ()
    assert result.changed_actions == ()
    assert result.to_text().splitlines() == [
        "+ action Sequence/Calibrate",
        "+ START --[IsReady]--> Sequence/Calibrate",
        "+ Sequence/Calibrate --[success]--> Sequence/Arm",
        "+ Sequence/Calibrate --[failure]--> FAILURE",
        "- START --[IsReady]--> Sequence/Arm",
        "transitions: 9 of 10 kept, 12 now; precision 0.75, recall 0.90, F1 0.82",
    ]


def test_changed_ports_and_notes_are_reported_per_field() -> None:
    new = OLD.replace('altitude="10"', 'altitude="15"').replace(
        "<Survey/>", '<RetryUntilSuccessful num_attempts="3"><Survey/></RetryUntilSuccessful>'
    )

    result = diff(OLD, new)

    assert [(c.key.path, dict(c.changes)) for c in result.changed_actions] == [
        ("Sequence/TakeOff", {"ports": ({"altitude": "10"}, {"altitude": "15"})}),
    ]
    # Survey moved under a decorator: its path changed.
    assert result.removed_actions == (action("Sequence/work/Survey"),)
    assert result.added_actions == (action("Sequence/work/RetryUntilSuccessful/Survey"),)


def test_a_renamed_node_is_removed_and_added() -> None:
    result = diff(OLD, OLD.replace("<Arm/>", '<Arm name="arm_motors"/>'))

    assert result.removed_actions == (action("Sequence/Arm"),)
    assert result.added_actions == (action("Sequence/arm_motors"),)


def test_an_action_that_only_moved_is_not_a_change() -> None:
    new = OLD.replace("<Arm/>", '<Sequence name="prepare"><Arm/></Sequence>')

    result = diff(OLD, new)

    assert result.moved_actions == ((action("Sequence/Arm"), action("Sequence/prepare/Arm")),)
    assert not result.changed
    assert result.to_text() == "> action Sequence/Arm moved to Sequence/prepare/Arm\nno change\n"
    assert result.to_markdown().endswith(
        "No change to the action graph.\n\n**Actions moved** (path changed only)\n\n"
        "- `Sequence/Arm` → `Sequence/prepare/Arm`\n"
    )
    assert result.to_dict()["actions"]["moved"] == [
        {
            "from": {"path": "Sequence/Arm", "label": "Arm"},
            "to": {"path": "Sequence/prepare/Arm", "label": "Arm"},
        }
    ]


def test_moves_that_are_ambiguous_are_a_removal_and_an_addition() -> None:
    old = "<Fallback><Sequence><Act/></Sequence><Sequence><Act/></Sequence></Fallback>"
    new = "<Fallback><Inverter><Act/></Inverter><Act/><Act/></Fallback>"

    result = diff(old, new)

    assert result.moved_actions == ()
    assert len(result.removed_actions) == 2


def test_a_moved_action_is_named_by_its_new_path_in_other_changes() -> None:
    new = OLD.replace("<Arm/>", '<Sequence name="prepare"><Arm/><Check/></Sequence>')

    result = diff(OLD, new)

    assert result.moved_actions == ((action("Sequence/Arm"), action("Sequence/prepare/Arm")),)
    assert "+ Sequence/prepare/Arm --[success]--> Sequence/prepare/Check" in result.to_text()


def test_a_changed_label_on_the_same_path() -> None:
    old = '<Sequence><Act name="go"/></Sequence>'
    new = '<Sequence><Move name="go"/></Sequence>'

    result = diff(old, new)

    assert [dict(c.changes) for c in result.changed_actions] == [{"type": ("Act", "Move")}]


def test_a_step_whose_guard_changed_is_one_change() -> None:
    result = diff(OLD, OLD.replace("<IsReady/>", "<IsClear/>"))

    assert (result.added_transitions, result.removed_transitions) == ((), ())
    assert [(str(c.source), c.outcome, str(c.target)) for c in result.changed_guards] == [
        ("START", None, "Sequence/Arm"),
        ("START", None, "FAILURE"),
    ]
    assert result.to_text().splitlines()[:4] == [
        "~ START --> Sequence/Arm: guard - [IsReady]",
        "~ START --> Sequence/Arm: guard + [IsClear]",
        "~ START --> FAILURE: guard - [not IsReady]",
        "~ START --> FAILURE: guard + [not IsClear]",
    ]


def test_ends_and_actions_that_become_unreachable() -> None:
    new = OLD.replace("<Survey/>", "<ForceSuccess><Survey/></ForceSuccess>")

    result = diff(OLD, new)

    assert result.became_unreachable == (action("Sequence/work/ReturnHome"),)
    assert result.became_reachable == ()
    assert "! Sequence/work/ReturnHome became unreachable" in result.to_text()

    back = diff(new, OLD)
    assert back.became_reachable == (action("Sequence/work/ReturnHome"),)


def test_a_terminal_that_becomes_unreachable() -> None:
    result = diff(
        "<Sequence><A/><B/></Sequence>",
        "<ForceSuccess><Sequence><A/><B/></Sequence></ForceSuccess>",
    )

    assert result.became_unreachable == (VertexKey(terminal="FAILURE"),)


def test_the_diff_reads_both_ways() -> None:
    new = OLD.replace("<ReturnHome/>", "<Land/>")
    forward, backward = diff(OLD, new), diff(new, OLD)

    assert forward.added_actions == backward.removed_actions
    assert forward.added_transitions == backward.removed_transitions
    assert (forward.score.precision, forward.score.recall) == (
        backward.score.recall,
        backward.score.precision,
    )


def test_score_of_empty_graphs() -> None:
    score = TransitionScore(matched=0, old=0, new=0)
    disjoint = TransitionScore(matched=0, old=2, new=3)

    assert (score.precision, score.recall, score.f1) == (1.0, 1.0, 1.0)
    assert (disjoint.precision, disjoint.recall, disjoint.f1) == (0.0, 0.0, 0.0)


def test_json_document() -> None:
    result = diff(OLD, OLD.replace('altitude="10"', 'altitude="15"').replace("<IsReady/>", ""))

    data = result.to_dict()

    assert data["schema"] == "beehave.graph-diff"
    assert data["version"] == 1
    assert data["changed"] is True
    assert data["old"]["graph_hash"] == beehave.graph_hash(graph(OLD))
    assert data["actions"]["changed"] == [
        {
            "path": "Sequence/TakeOff",
            "label": "TakeOff",
            "changes": {"ports": {"old": {"altitude": "10"}, "new": {"altitude": "15"}}},
        }
    ]
    assert data["transitions"]["removed"] == [
        {
            "from": {"terminal": "START"},
            "outcome": None,
            "to": {"terminal": "FAILURE"},
            "guard": [{"condition": "not IsReady", "key": "IsReady()", "holds": False}],
        }
    ]
    assert data["transitions"]["changed_guards"][0]["added"] == [[]]
    assert data["reachability"] == {"became_reachable": [], "became_unreachable": []}
    assert data["score"] == {
        "matched": 9,
        "old": 10,
        "new": 9,
        "precision": 1.0,
        "recall": 0.9,
        "f1": 0.9474,
    }
    assert json.loads(result.to_json()) == data


def test_markdown_for_a_pull_request() -> None:
    result = diff(OLD, OLD.replace("<ReturnHome/>", "<Land/>"))

    out = result.to_markdown()

    assert out.startswith("### Action graph diff: `Mission` → `Mission`\n\n| | Added |")
    assert "| Actions | 1 | 1 | 0 |" in out
    assert "**Actions added**\n\n- `Sequence/work/Land`\n" in out
    assert "**Actions removed**\n\n- `Sequence/work/ReturnHome`\n" in out
    assert "- `Sequence/work/Survey --[failure]--> Sequence/work/Land`" in out
    assert diff(OLD, OLD).to_markdown().endswith("No change to the action graph.\n")


def test_markdown_lists_changed_actions_guards_and_reachability() -> None:
    new = (
        OLD.replace('altitude="10"', 'altitude="15"')
        .replace("<IsReady/>", "<IsClear/>")
        .replace("<Survey/>", "<ForceSuccess><Survey/></ForceSuccess>")
    )

    out = diff(OLD, new).to_markdown()

    assert "- `Sequence/TakeOff`: ports `{altitude=10}` → `{altitude=15}`" in out
    assert "- `START --> Sequence/Arm`: removed `[IsReady]`, added `[IsClear]`" in out
    assert "- `Sequence/work/ReturnHome` became unreachable" in out


def test_an_unchanged_example_tree_and_its_v4_version() -> None:
    v3 = beehave.analyze(EXAMPLES / "aerial" / "drone_mission.xml").graph
    v4 = beehave.analyze(EXAMPLES / "aerial" / "drone_mission_v4.xml").graph

    assert not diff_graphs(v3, v4).changed


# --------------------------------------------------------------------- CLI ---


@pytest.fixture
def trees(tmp_path: Path) -> tuple[str, str]:
    old, new = tmp_path / "old.xml", tmp_path / "new.xml"
    xml = '<root><BehaviorTree ID="Mission">{}</BehaviorTree></root>'
    old.write_text(xml.format("<Sequence><Arm/><TakeOff/></Sequence>"), encoding="utf-8")
    new.write_text(xml.format("<Sequence><Arm/><Log/><TakeOff/></Sequence>"), encoding="utf-8")
    return str(old), str(new)


def test_cli_diff_prints_text(trees: tuple[str, str], capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["diff", *trees]) == 0

    assert capsys.readouterr().out.splitlines()[0] == "+ action Sequence/Log"


@pytest.mark.parametrize(
    ("fmt", "marker"), [("markdown", "### Action graph diff"), ("json", '"schema"')]
)
def test_cli_diff_formats(
    trees: tuple[str, str], fmt: str, marker: str, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["diff", *trees, "-f", fmt]) == 0

    assert marker in capsys.readouterr().out


def test_cli_diff_exit_code_and_output_file(
    trees: tuple[str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    out = tmp_path / "diff.md"

    assert main(["diff", *trees, "--exit-code", "-f", "markdown", "-o", str(out)]) == 3
    assert main(["diff", trees[0], trees[0], "--exit-code"]) == 0

    assert "**Actions added**" in out.read_text(encoding="utf-8")
    assert capsys.readouterr().out == "no change\n"


def test_cli_diff_uses_the_config(
    trees: tuple[str, str], tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    config = tmp_path / "beehave.yaml"
    config.write_text("bookkeeping:\n  Log: {never_fails: true}\n", encoding="utf-8")

    assert main(["diff", *trees, "-c", str(config), "--exit-code"]) == 0
    assert capsys.readouterr().out == "no change\n"


def test_cli_diff_reports_errors(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    missing = str(tmp_path / "missing.xml")

    assert main(["diff", missing, missing]) == 1
    assert "cannot read" in capsys.readouterr().err
    with pytest.raises(SystemExit):
        main(["diff", missing, missing, "--package", "nope"])


def test_text_shows_each_changed_field() -> None:
    old = '<RetryUntilSuccessful num_attempts="3"><Act name="go" speed="1"/></RetryUntilSuccessful>'
    new = (
        '<RetryUntilSuccessful num_attempts="5"><Move name="go" speed="2"/></RetryUntilSuccessful>'
    )

    assert diff(old, new).to_text().splitlines() == [
        "~ action RetryUntilSuccessful/go: type Act -> Move",
        "~ action RetryUntilSuccessful/go: ports {speed=1} -> {speed=2}",
        "~ action RetryUntilSuccessful/go: notes [retry ×3] -> [retry ×5]",
        "transitions: 3 of 3 kept, 3 now; precision 1.00, recall 1.00, F1 1.00",
    ]
