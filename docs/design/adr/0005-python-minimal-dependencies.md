# 0005. Python, with minimal dependencies

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

Our users are robotics engineers. Many run ROS 2 Humble (Python 3.10) or
Jazzy (Python 3.12). The tool must run in CI, on a laptop and next to a ground
station, and it should be trivial to install. It reads files that may come
from anywhere.

## Decision

- Python ≥ 3.10, typed (`mypy --strict`), shipped as a CLI plus a Python API.
- Runtime dependencies: the standard library plus PyYAML (for the config
  file). The CLI uses `argparse`, the parser uses `expat`, the JSON renderer
  uses `json`.
- The XML reader refuses any `DOCTYPE`, which rules out entity expansion and
  external entity attacks without needing `defusedxml`.
- Rendering to images is left to Mermaid and Graphviz; we output text.
- Guard simplification in Phase 2 may add an optional dependency (a BDD
  library or `sympy`), behind an extra.

## Consequences

- `pip install beehave-bt` pulls in one package.
- We keep Python 3.10 until ROS 2 Humble reaches end of life (May 2027).
- Some tooling (the docs builder) needs Python ≥ 3.11; that only affects
  contributors building the docs.
