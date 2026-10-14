# Configuration

Beehave works on any tree without configuration. One optional file per
project, `beehave.yaml`, tells it what the XML cannot.

```yaml
# beehave.yaml
conditions:
  - BatteryOK
  - IsEmergency
actions:
  - Probe
```

| Key | Meaning |
| --- | --- |
| `conditions` | Custom node types to treat as conditions. They become guards on edges, not boxes. |
| `actions` | Custom node types to treat as actions, even if the XML declares them as conditions. |

Unknown keys are an error, so a typo does not go unnoticed. A node cannot be
in both lists.

## Where Beehave looks

1. The file given with `-c` / `--config`.
2. Otherwise `beehave.yaml`, then `.beehave.yaml`, in the current directory.

From Python, pass a `beehave.Config` or use `beehave.load_config(path)`.

## How a node is classified

For each custom node type, the strongest signal wins:

1. this config file;
2. the explicit XML form, such as `<Condition ID="BatteryOK"/>`;
3. the `<TreeNodesModel>` section of the tree files;
4. its shape: no child means action, one child decorator, several control.

Built-in BT.CPP nodes (`Sequence`, `Inverter`, …) are always classified by
Beehave itself.

## Conditions in disguise

Some projects register nodes as actions that only check something: they
never change the world and only return success or failure. Listing them under
`conditions` turns them into guards, which usually makes the graph much
smaller and easier to read.
