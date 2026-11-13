"""Presets: what a custom control or decorator behaves like.

A project's own nodes are unknown to Beehave: a custom control is walked like
a Sequence and a custom decorator as transparent, and both are reported. When
a custom node behaves like a node Beehave knows, ``beehave.yaml`` says so and
the node is walked by that rule instead::

    nodes:
      PipelineSequence: pipeline_sequence      # short form
      KeepTrying:
        behaves_like: until_success
      RepeatUntilDone:
        behaves_like: loop_until_flag
        flag_port: done                       # the port that names the flag

A preset fixes the node's kind (control or decorator), how many children it
takes, and its walk rule. Presets whose loops or concurrency the graph cannot
draw yet are walked as far as the rules allow and always reported
(see :data:`PRESETS` and the configuration guide).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from beehave.model import NodeKind, Semantics

if TYPE_CHECKING:
    from collections.abc import Mapping


@dataclass(frozen=True)
class Preset:
    """A behaviour a custom node can borrow.

    Attributes:
        name: The preset's name in ``beehave.yaml``, e.g. ``"until_success"``.
        kind: Control or decorator.
        semantics: The walk rule the node gets.
        min_children: The fewest children the node may have.
        max_children: The most children the node may have, or ``None``.
        summary: One line saying what the node does.
        exact: Whether the walk reproduces every edge (some loop presets are
            exact only when their child runs no action).
        options: Option names, each with its allowed values (``None``: any
            text) and its default.
    """

    name: str
    kind: NodeKind
    semantics: Semantics
    min_children: int
    max_children: int | None
    summary: str
    exact: bool = True
    options: Mapping[str, tuple[tuple[str, ...] | None, str]] = field(default_factory=dict)


@dataclass(frozen=True)
class NodePreset:
    """One ``nodes:`` entry of the config: a custom node type and its preset.

    Attributes:
        behaves_like: The preset's name (aliases resolved).
        options: The preset's options, with defaults filled in.
    """

    behaves_like: str
    options: Mapping[str, str] = field(default_factory=dict)

    @property
    def preset(self) -> Preset:
        """The preset itself."""
        return PRESETS[self.behaves_like]


def _control(
    name: str,
    semantics: Semantics,
    summary: str,
    *,
    children: tuple[int, int | None] = (1, None),
    exact: bool = True,
) -> Preset:
    return Preset(name, NodeKind.CONTROL, semantics, *children, summary, exact)


def _decorator(
    name: str,
    semantics: Semantics,
    summary: str,
    *,
    exact: bool = True,
    options: Mapping[str, tuple[tuple[str, ...] | None, str]] | None = None,
) -> Preset:
    return Preset(name, NodeKind.DECORATOR, semantics, 1, 1, summary, exact, options or {})


_LIST: tuple[Preset, ...] = (
    # Built-in controls.
    _control("sequence", Semantics.SEQUENCE, "BT.CPP Sequence"),
    _control(
        "sequence_with_memory",
        Semantics.SEQUENCE_WITH_MEMORY,
        "BT.CPP SequenceWithMemory (SequenceStar in v3)",
    ),
    _control(
        "reactive_sequence", Semantics.REACTIVE_SEQUENCE, "BT.CPP ReactiveSequence", exact=False
    ),
    _control("fallback", Semantics.FALLBACK, "BT.CPP Fallback"),
    _control(
        "reactive_fallback", Semantics.REACTIVE_FALLBACK, "BT.CPP ReactiveFallback", exact=False
    ),
    _control("if_then_else", Semantics.IF_THEN_ELSE, "BT.CPP IfThenElse", children=(2, 3)),
    _control(
        "while_do_else",
        Semantics.WHILE_DO_ELSE,
        "BT.CPP WhileDoElse",
        children=(2, 3),
        exact=False,
    ),
    _control("try_catch", Semantics.TRY_CATCH, "BT.CPP v4 TryCatch", children=(2, None)),
    _control("parallel", Semantics.PARALLEL, "BT.CPP Parallel", exact=False),
    _control("parallel_all", Semantics.PARALLEL_ALL, "BT.CPP v4 ParallelAll", exact=False),
    _control(
        "pipeline_sequence",
        Semantics.PIPELINE_SEQUENCE,
        "Nav2 PipelineSequence: earlier children are ticked again while a later one runs",
        exact=False,
    ),
    _control(
        "round_robin",
        Semantics.ROUND_ROBIN,
        "Nav2 RoundRobin: a Fallback that starts after the child that last succeeded",
        exact=False,
    ),
    # Generic controls.
    _control(
        "parallel_first_success",
        Semantics.PARALLEL_FIRST_SUCCESS,
        "runs every child at once; succeeds when one succeeds, fails when all fail",
        exact=False,
    ),
    # Built-in decorators.
    _decorator("inverter", Semantics.INVERTER, "BT.CPP Inverter"),
    _decorator("force_success", Semantics.FORCE_SUCCESS, "BT.CPP ForceSuccess"),
    _decorator("force_failure", Semantics.FORCE_FAILURE, "BT.CPP ForceFailure"),
    _decorator("pass_through", Semantics.PASS_THROUGH, "returns its child's result unchanged"),
    _decorator("retry", Semantics.RETRY, "BT.CPP RetryUntilSuccessful", exact=False),
    _decorator("repeat", Semantics.REPEAT, "BT.CPP Repeat", exact=False),
    _decorator(
        "keep_running_until_failure",
        Semantics.KEEP_RUNNING_UNTIL_FAILURE,
        "BT.CPP KeepRunningUntilFailure",
        exact=False,
    ),
    _decorator("timeout", Semantics.TIMEOUT, "BT.CPP Timeout", exact=False),
    _decorator("run_once", Semantics.RUN_ONCE, "BT.CPP v4 RunOnce", exact=False),
    # Generic decorators.
    _decorator(
        "until_success",
        Semantics.UNTIL_SUCCESS,
        "ticks its child again after each failure, until it succeeds; never fails",
        exact=False,
    ),
    _decorator(
        "poll_until_success",
        Semantics.UNTIL_SUCCESS,
        "checks its child, usually a condition, until it succeeds; never fails",
        exact=False,
    ),
    _decorator(
        "loop_until_flag",
        Semantics.LOOP_UNTIL_FLAG,
        "ticks its child again and again until a blackboard flag is set, then exits",
        exact=False,
        options={
            "flag_port": (None, "flag"),
            "exit": (("success", "failure"), "success"),
        },
    ),
)

PRESETS: Mapping[str, Preset] = {preset.name: preset for preset in _LIST}
"""Every preset, by name."""

ALIASES: Mapping[str, str] = {"keep_running_until_success": "until_success"}
"""Other names accepted for a preset."""


def resolve(name: str) -> Preset | None:
    """Return the preset called ``name`` (or one of its aliases), if there is one."""
    return PRESETS.get(ALIASES.get(name, name))


__all__ = ["ALIASES", "PRESETS", "NodePreset", "Preset", "resolve"]
