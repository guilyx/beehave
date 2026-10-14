# 0006. Publish as `beehave-bt`

- **Status:** Accepted
- **Date:** 2026-10-14

## Context

The name `beehave` is already taken on PyPI by an unrelated testing library.
There is also a popular behavior tree addon for the Godot game engine called
Beehave. Users searching for "beehave behavior tree" may find it first.

## Decision

- The PyPI distribution is **`beehave-bt`**.
- The import name is `beehave` and the command is `beehave`.
- The README and the docs say in the first lines that this project is about
  BehaviorTree.CPP and ROS 2 robots, and is not the Godot addon.

## Consequences

- `pip install beehave-bt`, then `import beehave` and `beehave graph …`.
- If the name causes real confusion, renaming before 1.0 is still cheap.
