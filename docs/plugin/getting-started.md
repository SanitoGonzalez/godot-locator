---
sidebar_position: 2
---

# Getting Started

Enable the addon in *Project Settings → Plugins*. It registers a `Locator` autoload that opens a local WebSocket server when the game runs.

| Env | Description | Default |
| --- | ----------- | ------- |
| `GODOT_LOCATOR_PORT` | port the runtime service binds to | `8282` |
| `GODOT_LOCATOR_HOST` | bind address — `127.0.0.1` / `::1` for loopback, `0.0.0.0` / `::` for all interfaces (v4 / v6) | `127.0.0.1` |
| `GODOT_LOCATOR_SERVER_ENABLED` | set to `false` to skip the WebSocket server. The autoload's [direct API](#direct-api) stays available to your code | `true` |

### Snapshot

Structured snapshot of the SceneTree. Only `Control` nodes are emitted; non-Control parents (`Window`, `CanvasLayer`, `Node2D`…) are walked through transparently so Controls nested under them still surface.

The plugin returns JSON of shape `{tree, context?}`:

```json
{
  "tree": [
    {"class": "VBoxContainer", "name": "Form", "children": [
      {"class": "Label", "name": "Title", "text": "Welcome", "children": []},
      {"class": "LineEdit", "name": "NameInput", "ref": "e1",
       "attrs": {"placeholder": "Name"}, "children": []},
      {"class": "Button", "name": "SubmitButton", "text": "Submit",
       "ref": "e2", "flags": ["disabled"], "children": []}
    ]}
  ]
}
```

Each node has `class` and `children`; `name`, `text`, `ref`, `attrs`, and `flags` are emitted only when non-empty. Refs (`eN`) are stable instance ids — once issued, they keep pointing at the same node for follow-up `locate`/control calls — and are off by default; pass `tag_ref: true` (Playwright-style) to have them emitted for interactive nodes (`LineEdit` / `TextEdit` / `BaseButton`) and any node implementing the custom-format hook below.

The bundled CLI / MCP packages render this into a YAML-style text representation for agents:

```
- VBoxContainer #Form:
  - Label #Title "Welcome"
  - LineEdit #NameInput [ref=e1, placeholder="Name"]
  - Button #SubmitButton "Submit" [ref=e2, disabled]
```

#### Options
| Name | Description | Default |
| ---- | ----------- | ------- |
| depth | maximum traversal depth from the root | 0 (all) |
| skip_invisible | omit nodes whose `visible` is false (and their subtrees) | true |
| tag_ref | emit `ref=eN` markers for interactive / custom-format nodes | false |

#### Game context

Attach game-defined state (HP, current world, score…) to every snapshot by assigning a `Callable` to `Locator.context_provider`. The returned `Dictionary` lands at `snapshot.context`:

```gdscript
func _ready() -> void:
    Locator.context_provider = func():
        return {"hp": "%d/%d" % [hp, hp_max], "world": world_name}
```

```yaml
### Context
hp: 100/200
world: Castle of Death

### Snapshot
- ...
```

Non-Dictionary returns and unset / invalid callables are silently dropped — no `context` key in the snapshot.

#### Custom node formatting

To extend the snapshot for your own node classes, implement `_godot_locator_format() -> Dictionary` (or `_GodotLocatorFormat()` from C#). Any node with this method auto-gets a ref.

```gdscript
class_name HealthBar extends Control

func _godot_locator_format() -> Dictionary:
    return {
        "text": "%d/%d" % [current, maximum],
        "attrs": {"pct": int(100.0 * current / maximum)},
        "flags": ["critical"] if current < maximum * 0.2 else [],
    }
```

```csharp
using Godot;
using Godot.Collections;

public partial class HealthBar : Control
{
    public Dictionary _GodotLocatorFormat() => new()
    {
        ["text"] = $"{Current}/{Maximum}",
        ["attrs"] = new Dictionary { ["pct"] = (int)(100.0 * Current / Maximum) },
        ["flags"] = Current < Maximum * 0.2 ? new Array { "critical" } : new Array(),
    };
}
```

Renders as:

```yaml
- HealthBar #Player "30/100" [ref=e7, pct=30, critical]
```

| Field | Effect |
| ----- | ------ |
| `text` | overrides the built-in positional `"…"` (Label/Button/RichTextLabel/LineEdit default) |
| `attrs` | merged into the trailing bracket. `int`/`float`/`bool` values render unquoted; everything else is stringified and quoted. `null` values are dropped |
| `flags` | bare tokens appended after `attrs` in the bracket (e.g. `BaseButton.disabled`) |

All three keys are optional — return any subset.

**Class names** in the snapshot are resolved in this order: GDScript `class_name` (via `Script.get_global_name()`) → the project's global class registry (path lookup) → for `.cs` scripts, the filename basename → engine class (`get_class()`). The `.cs` step is a fallback because Godot 4.6's C# binding doesn't expose user class names to GDScript through either of the first two paths. Keep the standard C# convention of one `public partial class FooBar` per `FooBar.cs` and your custom node will appear as `FooBar` in the snapshot; otherwise it falls through to the engine base type (e.g. `Button`).
