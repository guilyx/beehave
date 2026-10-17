<!--
Thanks for contributing to Beehave. Please make the title a Conventional
Commit, for example "fix(walk): keep the guard when a Fallback ends in a
condition". See CONTRIBUTING.md for the details.
-->

## What

<!-- What does this pull request change? Keep it to one change. -->

## Why

<!-- The problem it solves, or the behaviour it fixes. -->

Closes #

## How it was tested

<!-- Which tests did you add first, and what did they show before the fix?
For output changes, mention the snapshot files you updated. -->

## Checklist

- [ ] I wrote the tests first and watched them fail for the right reason.
- [ ] `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy` and
      `uv run pytest --cov` pass locally.
- [ ] I reviewed every snapshot diff (if `--snapshot-update` was used).
- [ ] The docs are updated for any user-visible change.
- [ ] `CHANGELOG.md` has a line under `## [Unreleased]` (if users would notice).
- [ ] The change stays within the current roadmap phase, or was agreed in the
      linked issue.
- [ ] Design changes come with an ADR in `docs/design/adr/`.
