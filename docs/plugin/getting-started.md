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
| `GODOT_LOCATOR_EVAL_ENABLED` | set to `true` to allow the `evaluate` wire method to run GDScript expressions in the running game. See [Eval](#eval) below | `false` |

### Release builds

The plugin is **off in release exports** unless you opt in. Add `locator` to *Project → Export → [preset] → Features → Custom (comma-separated)* to enable it for a specific preset (e.g. an internal QA build). Debug builds always run the plugin regardless of the tag.

When the gate is closed, no WebSocket server starts and no port is opened — the `Locator` autoload exists but its `_ready()` returns early. Direct API calls from your own code (`Locator.snapshot()`, `Locator.context_provider = …`) are safe to keep in shipping code; they just won't reach a server.

### Eval

The `evaluate` method runs a single GDScript expression inside the running game and returns its value. Useful for inspecting state that isn't in the snapshot (HP, inventory, internal flags, current scene, etc.):

```bash
godot-locator-cli eval "get_tree().current_scene.name"
godot-locator-cli eval --ref=e5 "node.text"
```

Because expressions have full read access to the entire game (and can call methods that mutate state), the wire method is **off by default**. Opt in by setting `GODOT_LOCATOR_EVAL_ENABLED=true` on the game process. Keep it off in shipping builds.

Two limitations to keep in mind:

- **GDScript syntax only.** Even on C# projects, write `node.get_name()`, not `node.GetName()` — Godot's `Expression` evaluator uses GDScript naming for everything.
- **Single expression.** No `var`/`func`/multi-line statements. To inspect more, chain calls (`get_tree().current_scene.find_child("Player").hp`) or expose a helper method on a node and call it.

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

Each node has `class` and `children`; `name`, `text`, `ref`, `attrs`, and `flags` are emitted only when non-empty. Refs (`eN`) are stable instance ids — once issued, they keep pointing at the same node for follow-up `locate`/control calls — and are off by default; pass `tag_ref: true` (Playwright-style) to have them emitted. A Control gets a ref when any of:

1. it's a built-in interactive — `LineEdit` / `TextEdit` / `BaseButton`,
2. it implements the [custom-format hook](#custom-node-formatting),
3. its script overrides `_gui_input`, or has a `gui_input` signal listener — the canonical signal that the Control handles its own input,
4. it sets `set_meta("godot_locator_ref", true)` — explicit opt-in (or `false` to opt out of any of the above).

Layout containers (`VBoxContainer`, `MarginContainer`, `PanelContainer`, …) don't pick up refs unless you opt them in. Custom Controls that draw and handle their own input — picker grids, drag rects, sliders — are caught automatically by rule 3.

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

#### Forcing or hiding refs

The auto-detect heuristic is best-effort. Override it on a per-Control basis with the `godot_locator_ref` meta:

```gdscript
# Force a ref on a Control the heuristic would skip — e.g. an empty hit area
# whose parent handles input.
my_hit_area.set_meta("godot_locator_ref", true)

# Hide a ref the heuristic would emit — e.g. a debug-only Button.
my_debug_btn.set_meta("godot_locator_ref", false)
```

The meta wins over every other rule (built-in classes, custom-format hook, `_gui_input` detection).

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
