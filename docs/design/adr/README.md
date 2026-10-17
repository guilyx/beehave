# Architecture decision records

An ADR records one decision: the context, what we chose, and what follows from
it. They are short, numbered, and never deleted. A decision that changes gets a
new ADR that supersedes the old one.

| ADR | Title | Status |
| --- | --- | --- |
| [0001](0001-record-architecture-decisions.md) | Record architecture decisions | Accepted |
| [0002](0002-one-model-many-parsers.md) | One internal model, many parsers | Accepted |
| [0003](0003-continuation-passing-walk.md) | A continuation-passing walk | Accepted |
| [0004](0004-approximate-and-report.md) | Approximate, and always report it | Accepted |
| [0005](0005-python-minimal-dependencies.md) | Python, with minimal dependencies | Accepted |
| [0006](0006-distribution-name.md) | Publish as `beehave-bt` | Accepted |
| [0007](0007-test-driven-with-a-reference-interpreter.md) | Test-driven, with a reference interpreter | Accepted |
| [0008](0008-formats-track.md) | Grow formats on their own track | Accepted |
| [0009](0009-bt-cpp-v4-skipped.md) | Read BT.CPP v4 with a third continuation for SKIPPED | Accepted |
| [0010](0010-py-trees-live-trees.md) | Read py_trees trees live, and import user code only on request | Accepted |

To propose a decision, copy [the template](template.md), take the next number,
and open a pull request. Discussion happens on the pull request.
