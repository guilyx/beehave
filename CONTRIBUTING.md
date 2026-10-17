# Contributing to Beehave

Thanks for taking the time to help. Beehave turns BehaviorTree.CPP trees into
action graphs that people trust instead of reading the XML, so every
contribution is held to one standard: **a wrong arrow is worse than no
graph.** That is why we work test-first and why the review focuses on
correctness before style.

This guide covers everything from a one-line typo fix to a new node type. If
something here is unclear, that is a bug in the guide: please tell us.

- [Ways to contribute](#ways-to-contribute)
- [Reporting a tree Beehave gets wrong](#reporting-a-tree-beehave-gets-wrong)
- [Scope and the roadmap](#scope-and-the-roadmap)
- [Project layout](#project-layout)
- [Development setup](#development-setup)
- [The test-first workflow](#the-test-first-workflow)
- [Adding support for a node type](#adding-support-for-a-node-type)
- [Documentation and design decisions](#documentation-and-design-decisions)
- [Commits and pull requests](#commits-and-pull-requests)
- [Licensing of contributions](#licensing-of-contributions)
- [How releases are made](#how-releases-are-made)

Everyone taking part in the project follows our
[Code of Conduct](CODE_OF_CONDUCT.md).

## Ways to contribute

- **Report a tree Beehave mishandles.** This is the most valuable contribution
  of all; see the next section.
- **Fix a bug or add a feature.** Look for issues labelled
  [`good first issue`](https://github.com/guilyx/beehave/labels/good%20first%20issue)
  or [`help wanted`](https://github.com/guilyx/beehave/labels/help%20wanted).
  Comment on the issue before you start so nobody duplicates the work.
- **Improve the docs.** Fixes to wording, examples and diagrams are always
  welcome, and are a good way to learn the codebase.
- **Ask and answer questions** in
  [GitHub Discussions](https://github.com/guilyx/beehave/discussions).

For anything bigger than a bug fix, please open an issue or a discussion first.
It is much easier to agree on the approach before the code exists.

## Reporting a tree Beehave gets wrong

Use the **"Beehave produced a wrong or confusing graph"** issue form. A good
report has:

1. **The smallest tree that shows the problem.** Start from your real tree and
   delete nodes until removing any more makes the problem go away. Rename
   anything you cannot share (`Action1`, `IsReady`, ...). Ten lines of XML get
   fixed far faster than five hundred.
2. **The exact command** you ran, including any `beehave.yaml` you used.
3. **What Beehave printed** (use `-f text`; it is the easiest to read in an
   issue).
4. **What you expected**, ideally in the same `A --[outcome]--> B` form, and
   why: what does BehaviorTree.CPP actually do with this tree?
5. **Versions:** `beehave --version` and the BehaviorTree.CPP version the tree
   is written for.

A minimal tree looks like this:

```xml
<root main_tree_to_execute="Main">
  <BehaviorTree ID="Main">
    <Fallback>
      <Sequence>
        <IsReady/>
        <DoThing/>
      </Sequence>
      <Recover/>
    </Fallback>
  </BehaviorTree>
</root>
```

That tree often becomes the regression test for the fix, so it pays to keep
it small. Please do not attach trees you are not allowed to share publicly.

Security problems are different: report them privately as described in
[SECURITY.md](SECURITY.md), never in a public issue.

## Scope and the roadmap

Beehave grows in phases. Each phase has a gate we must pass before the next
one starts (see [the roadmap](docs/design/roadmap.md)):

| Phase | What it delivers | Status |
| --- | --- | --- |
| 1. Action graph | Parse, flatten, walk and render BT.CPP v3 trees: actions with success and failure edges | **current** |
| 2. Guards and metrics | Simplified guard formulas, exact rules for reactive nodes, loops and `Parallel`, a gap report, a BT.CPP v4 parser | next |
| 3. Operator view | Operator-friendly labels, a collapsed phase view, a JSON export for ground-control UIs, live status | later |
| 4. LTL checks | Safety properties checked with a model checker | optional |

**Pull requests should stay within the current phase** unless the change was
discussed and agreed in an issue first. A great Phase 2 idea is welcome as an
issue (pick the phase in the feature request form); it will not be merged
early, because it would make the Phase 1 gate harder to judge.

Beehave reads trees; it does not edit or generate them, and it is not a
replacement for Groot2. Changes in that direction are out of scope.

## Project layout

```text
src/beehave/
├── parsers/          # 1. Parse: XML -> Document
│   ├── btcpp_v3.py   #    BT.CPP v3 parser and the BUILTINS node registry
│   └── _xml.py       #    safe XML loading with source locations
├── model.py          # the shared tree model: Document, Tree, Node, NodeKind, Semantics
├── flatten.py        # 2. Flatten: inline SubTree / SubTreePlus with port remapping
├── walk.py           # 3. Walk: FlatTree -> ActionGraph (continuation-passing)
├── graph.py          # ActionGraph, Vertex, Edge, guards
├── render/           # 4. Render: text, Mermaid, DOT, JSON
├── stats.py          # Phase 1 metrics: size, reduction, longest guard, breakage
├── diagnostics.py    # warnings about approximations, with source locations
├── config.py         # beehave.yaml
├── api.py            # beehave.analyze(): parse + flatten + walk in one call
├── errors.py         # the exception hierarchy
└── cli.py            # the `beehave` command (graph, stats, trees)

tests/
├── unit/             # one file per step, small trees written inline
│   └── __snapshots__/  # syrupy snapshots of the rendered output
├── property/         # Hypothesis tests against a reference interpreter
├── integration/      # Beehave on the public trees, pinned as snapshots
└── fixtures/
    └── public/       # byte-identical third-party trees, under their own licenses

examples/             # aerial, mobile and manipulation trees, tested in tests/unit/test_examples.py
scripts/              # refresh the graphs shown in the docs, sync brand assets

docs/
├── guide/            # user documentation
├── design/           # architecture, phase specifications, roadmap
│   └── adr/          # architecture decision records
└── research/         # notes on BT.CPP formats
```

Each step has one input type and one output type, so each can be tested on
its own. The [architecture page](docs/design/architecture.md)
explains the pipeline in more detail.

## Development setup

You need [uv](https://docs.astral.sh/uv/getting-started/installation/) and
Git. uv installs the right Python for you.

```sh
git clone https://github.com/<you>/beehave.git
cd beehave
uv sync --group dev          # creates .venv with the test and lint tools
uv run beehave --version     # the CLI, from your checkout
```

We support Python 3.10 to 3.14. Python 3.10 stays until ROS 2 Humble reaches
end of life (May 2027), so do not use syntax or standard library features
newer than 3.10 (`ruff` and `mypy` are configured to catch this).

### Pre-commit hooks

We use [prek](https://github.com/j178/prek), a fast drop-in replacement for
`pre-commit` that reads the same `.pre-commit-config.yaml`:

```sh
uv tool install prek
prek install                 # run the hooks on every commit
prek run --all-files         # or run them by hand
```

`pre-commit` itself works too if you already have it.

### The checks

These are exactly what CI runs. Run them before you push:

```sh
uv run ruff format --check .   # formatting (drop --check to fix)
uv run ruff check .            # lint (add --fix for the safe fixes)
uv run mypy                    # strict type checking of src/ and tests/
uv run pytest --cov            # tests, with the 95% coverage floor
```

CI also runs the tests on Python 3.10 to 3.14 and on macOS and Windows, and
checks that the built wheel installs and runs. All of this is summarised by
one required check, `ci-ok`.

## The test-first workflow

We work test-first ([ADR 0007](docs/design/adr/0007-test-driven-with-a-reference-interpreter.md)):

1. **Red.** Write a test that describes the behaviour you want, and watch it
   fail for the right reason. For a bug, the test is the minimal tree from
   the report.
2. **Green.** Write the simplest code that makes it pass.
3. **Refactor.** Clean up with the tests as a safety net.

Pull requests that change behaviour without a test will be asked for one.

### Unit tests: `tests/unit/`

One file per step (`test_parser_v3.py`, `test_flatten.py`, `test_walk.py`,
...). Trees are written inline and expected graphs are written as edges, so
each test reads like the graph it expects:

```python
def test_fallback_runs_the_next_child_on_failure() -> None:
    assert edges(graph("<Fallback><A/><B/></Fallback>")) == [
        "START -> A",
        "A -success-> SUCCESS",
        "A -failure-> B",
        "B -success-> SUCCESS",
        "B -failure-> FAILURE",
    ]
```

Name tests after the behaviour (`test_inverter_swaps_outcomes`), not the
function under test.

### Property tests: `tests/property/`

`test_walk_matches_execution.py` generates random trees and random outcomes
with [Hypothesis](https://hypothesis.readthedocs.io/), runs them in a small
reference interpreter, and checks that following the action graph visits the
same actions and ends with the same result, with exactly one matching edge at
every step. The interpreter is the executable definition of "what the tree
does", so keep it small and obviously correct.

If Hypothesis finds a failure, it prints the smallest example it could find.
Turn that example into a unit test before you fix the bug.

### Snapshot tests

The rendered text, Mermaid, DOT and JSON for reference trees are pinned with
[syrupy](https://github.com/syrupy-project/syrupy) under
`tests/unit/__snapshots__/`. When you change the output on purpose:

```sh
uv run pytest --snapshot-update
git diff tests/unit/__snapshots__/
```

**Review the diff line by line** and commit it with your change. Reviewers
read snapshot diffs as carefully as code: they are the user-visible output.
Never run `--snapshot-update` just to make a red test green.

Tests that compare against files in `tests/golden/` are refreshed the same
way, with `uv run pytest --update-golden`.

## Adding support for a node type

Say BT.CPP has a built-in node Beehave does not know yet. The change touches
four places, each driven by a failing test:

1. **Open an issue** with the node's name, a link to its implementation in
   BT.CPP, and a minimal tree that uses it. Agree on whether Phase 1 can model
   it exactly or must approximate it.
2. **Parser.** In `tests/unit/test_parser_v3.py`, write a test that the node
   parses with the right `NodeKind` and `Semantics` and that a wrong number of
   children is rejected. Then register it in `BUILTINS` in
   `src/beehave/parsers/btcpp_v3.py` with the `_control`, `_decorator` or
   `_leaf` helper and its child limits. If its behaviour is genuinely new, add
   a member to `Semantics` in `src/beehave/model.py`.
3. **Walk.** In `tests/unit/test_walk.py`, write the edges you expect. Then add
   the rule to `_Walker.compile` in `src/beehave/walk.py`. Most rules are a
   choice of success and failure continuations; the
   [walk rules table](docs/design/phase-1.md#the-walk)
   shows the existing ones.
   - If Phase 1 cannot model the node exactly, walk it with the closest
     approximation **and** add it to `_APPROXIMATIONS` with a one-line
     explanation, so users get a diagnostic. Beehave never approximates
     silently ([ADR 0004](docs/design/adr/0004-approximate-and-report.md)).
   - If the rule is exact, teach the reference interpreter in
     `tests/property/test_walk_matches_execution.py` about the node and add it
     to the tree strategy. An exact rule is not done until the property test
     covers it.
4. **Docs and changelog.** Add the node to the *Node support* table (and the
   walk rules table if it has a new rule) in `docs/design/phase-1.md`, and add
   a line under `## [Unreleased]` in `CHANGELOG.md`.

Custom (user-defined) nodes need no code: they are classified by
`beehave.yaml`, the XML form or `<TreeNodesModel>`.

## Documentation and design decisions

The docs live in `docs/` and are built with [Zensical](https://zensical.org/)
from `mkdocs.yml`. The docs tools need Python 3.11 or newer:

```sh
uv run --python 3.13 --group docs zensical serve            # live preview
uv run --python 3.13 --group docs zensical build --clean    # what CI runs
```

- User-facing behaviour changes need a docs update in the same pull request.
- Write short sentences and show real output. If you add an example, run it
  and paste what Beehave actually prints.
- **Design decisions are recorded as ADRs** in `docs/design/adr/`. A change to
  the architecture, the tree model, the walk, or the public API needs an ADR:
  copy `docs/design/adr/template.md`, take the next number, and open it as its
  own pull request (or as the first commit of the feature pull request).
  Discussion happens on that pull request. ADRs are never deleted; a decision
  that changes gets a new ADR that supersedes the old one.

## Commits and pull requests

### Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```text
<type>(<optional scope>): <summary in the imperative, lower case, no period>
```

| Type | For |
| --- | --- |
| `feat` | a new user-visible capability |
| `fix` | a bug fix |
| `docs` | documentation only |
| `test` | tests only |
| `refactor` | code changes that neither fix a bug nor add a feature |
| `perf` | performance |
| `build` | packaging, dependencies, uv |
| `ci` | GitHub Actions and other automation |
| `chore` | anything else |

Common scopes: `parser`, `flatten`, `walk`, `render`, `stats`, `cli`, `api`,
`config`. Mark breaking changes with `!` (`feat(cli)!: ...`) and explain them
in a `BREAKING CHANGE:` footer. Examples from our history:

```text
feat(flatten): inline SubTree and SubTreePlus with port remapping
test: check the action graph against a reference interpreter
```

### Pull requests

- Keep each pull request to one change. Small pull requests get reviewed
  quickly; large ones wait.
- Link the issue it closes (`Closes #123`).
- Fill in the pull request template checklist: tests first, all checks green,
  docs and `CHANGELOG.md` updated, within the current phase.
- Add a line to `CHANGELOG.md` under `## [Unreleased]` for anything a user
  would notice. Tests, CI and refactors usually do not need one.
- `ci-ok` must be green before merge. A maintainer reviews every pull request.
- Make the pull request title a Conventional Commit too: it becomes the
  commit message when the pull request is squash-merged.
- Be patient and kind in review, in both directions. Reviews are about the
  code, never the person.

## Licensing of contributions

Beehave is licensed under the [Apache License 2.0](LICENSE). We do not ask
for a Contributor License Agreement or a DCO sign-off. Section 5 of the
license already says that any contribution you intentionally submit to the
project is licensed under the same terms ("inbound = outbound"). By opening a
pull request, you confirm that you have the right to submit the work under
that license.

If you add third-party files (for example, test trees from another project),
keep their license next to them under `tests/fixtures/public/` and say so in
the pull request.

## How releases are made

Releases are cut by a maintainer from `main`:

1. Set the version: `uv version 0.2.0` (this updates `pyproject.toml` and
   `uv.lock`).
2. In `CHANGELOG.md`, rename `## [Unreleased]` to `## [0.2.0] - YYYY-MM-DD`,
   add a fresh empty `## [Unreleased]` above it, and update the links at the
   bottom.
3. Open a pull request `chore: release 0.2.0`, and merge it once `ci-ok` is
   green.
4. Tag the merge commit and push the tag:
   `git tag -s v0.2.0 -m "Beehave 0.2.0" && git push origin v0.2.0`.
5. The [release workflow](.github/workflows/release.yml) runs CI again, checks
   that the tag matches the version, builds the sdist and wheel, publishes them
   to PyPI with trusted publishing and attestations, signs them with Sigstore,
   and creates the GitHub Release with the signed files and the changelog
   section as release notes.

Versions follow [PEP 440](https://peps.python.org/pep-0440/) and
[Semantic Versioning](https://semver.org/). While we are at 0.x, a minor
release may contain breaking changes; they are always called out in the
changelog. Pre-releases (`v0.2.0rc1`) follow the same steps, with their own
`## [0.2.0rc1]` changelog section, and are marked as pre-releases on GitHub.
