# Governance

This document describes how Beehave is run: who decides, how decisions are
made, and how contributors can take on more responsibility. It will change as
the project grows; changes to it go through a pull request like any other.

## Roles

### Users

Anyone who uses Beehave. Users help the project most by reporting trees that
Beehave gets wrong, asking questions in Discussions, and telling us what they
need.

### Contributors

Anyone who contributes to the project: code, tests, docs, issue reports,
reviews, answers in Discussions, or design feedback. No permission is needed;
see [CONTRIBUTING.md](CONTRIBUTING.md).

### Committers

Contributors who have shown sustained, high-quality involvement and have been
given write access to the repository. Committers:

- review and merge pull requests (never their own without a second review);
- triage issues and discussions, and apply labels;
- uphold the [Code of Conduct](CODE_OF_CONDUCT.md) and the quality bar in
  CONTRIBUTING.md (test-first, every check green).

### Maintainer

Beehave is currently a **maintainer-led** project. The maintainer is
Erwin Lejeune ([@guilyx](https://github.com/guilyx)), who:

- sets the roadmap and decides when a phase gate has been passed;
- has the final say when consensus cannot be reached;
- manages releases, the repository settings and the project's accounts
  (PyPI, GitHub);
- handles Code of Conduct reports and security reports.

The maintainer is also listed in [`.github/CODEOWNERS`](.github/CODEOWNERS).

## How decisions are made

Most decisions are made in the open, on GitHub, by lazy consensus: a proposal
that gets no objection after a reasonable time (usually a week) is accepted.

- **Bugs and small changes** are decided on the pull request itself.
- **Features and changes of direction** start as an issue or a
  [Discussion](https://github.com/guilyx/beehave/discussions), so the
  approach is agreed before the code is written.
- **Design changes** (the architecture, the tree model, the walk, the public
  Python API, the CLI's behaviour or output formats, supported Python
  versions) need a design document: an architecture decision record (ADR) in
  `docs/design/adr/`, following the template there. The ADR is discussed on
  its pull request and is accepted when it is merged. Larger designs may also
  get a page in `docs/design/` (like the phase specifications).
- **Scope** follows the [roadmap](docs/design/roadmap.md). Work beyond the
  current phase needs agreement in an issue first.

If people disagree, we try to resolve it on the issue or pull request by
looking at the evidence: a failing test, a real tree, the BT.CPP source. If
that does not settle it, the maintainer decides and records the reasoning
(in an ADR when it is a design decision).

## Becoming a committer

There is no fixed checklist, but committers are usually people who have:

- landed several non-trivial pull requests that followed the test-first
  workflow;
- reviewed other people's pull requests helpfully;
- shown good judgment about scope and correctness, and respect for the Code
  of Conduct.

Any committer or the maintainer can propose a contributor, and contributors
may ask to be considered. The maintainer makes the decision after checking
with existing committers and with the person proposed. New committers are
announced in Discussions.

Committers who become inactive for six months may be moved to an emeritus
status; they keep the credit and can return by asking. Access may also be
removed for breaches of the Code of Conduct.

## Changing the maintainer model

If the project grows to several active committers, we expect to move from a
single maintainer to a small group of maintainers who decide by consensus.
That change will be made through a pull request to this document.

## Code of Conduct

Everyone involved in the project is expected to follow the
[Code of Conduct](CODE_OF_CONDUCT.md). The maintainer, and any committers
the maintainer appoints to help, act as its Community Moderators.
