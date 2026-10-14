# Issue and pull request labels

GitHub does not create labels from files, so this is the reference list. The
issue forms apply `bug`, `enhancement` and `triage`; the rest are applied
during triage.

| Label | Colour | Meaning |
| --- | --- | --- |
| `bug` | `d73a4a` | Something does not work as documented. |
| `enhancement` | `a2eeef` | A new capability or an improvement. |
| `triage` | `fbca04` | New; a maintainer has not looked at it yet. |
| `good first issue` | `7057ff` | Small, well-defined, with pointers to the code. |
| `help wanted` | `008672` | We would welcome a contribution here. |
| `phase-1` | `0e8a16` | Phase 1: action graph (current). |
| `phase-2` | `1d76db` | Phase 2: guards and metrics. |
| `phase-3` | `5319e7` | Phase 3: operator view. |
| `phase-4` | `b60205` | Phase 4: LTL checks (optional). |
| `parser` | `c5def5` | Reading tree files (`beehave.parsers`). |
| `walk` | `c5def5` | Building the action graph (`beehave.flatten`, `beehave.walk`). |
| `render` | `c5def5` | Output formats (`beehave.render`). |
| `docs` | `0075ca` | Documentation. |
| `dependencies` | `0366d6` | Dependency updates (used by Dependabot). |

## Creating them

With the [GitHub CLI](https://cli.github.com/), from a checkout:

```sh
gh label create bug              --color d73a4a --description "Something does not work as documented." --force
gh label create enhancement      --color a2eeef --description "A new capability or an improvement." --force
gh label create triage           --color fbca04 --description "New; a maintainer has not looked at it yet." --force
gh label create "good first issue" --color 7057ff --description "Small, well-defined, with pointers to the code." --force
gh label create "help wanted"    --color 008672 --description "We would welcome a contribution here." --force
gh label create phase-1          --color 0e8a16 --description "Phase 1: action graph (current)." --force
gh label create phase-2          --color 1d76db --description "Phase 2: guards and metrics." --force
gh label create phase-3          --color 5319e7 --description "Phase 3: operator view." --force
gh label create phase-4          --color b60205 --description "Phase 4: LTL checks (optional)." --force
gh label create parser           --color c5def5 --description "Reading tree files." --force
gh label create walk             --color c5def5 --description "Building the action graph." --force
gh label create render           --color c5def5 --description "Output formats." --force
gh label create docs             --color 0075ca --description "Documentation." --force
gh label create dependencies     --color 0366d6 --description "Dependency updates." --force
```

`--force` updates a label that already exists, so the script is safe to run
again after changing this list.
