# godot-locator

A Playwright-inspired locator API for Godot's runtime SceneTree

## [Plugin](addons/godot-locator/)

Enable the addon in *Project Settings → Plugins*. It registers a `Locator` autoload that opens a local WebSocket server when the game runs.

| Env | Description | Default |
| --- | ----------- | ------- |
| `GODOT_LOCATOR_PORT` | port the runtime service binds to | `8282` |
| `GODOT_LOCATOR_HOST` | bind address — `127.0.0.1` / `::1` for loopback, `0.0.0.0` / `::` for all interfaces (v4 / v6) | `127.0.0.1` |
| `GODOT_LOCATOR_SERVER_ENABLED` | set to `false` to skip the WebSocket server. The autoload's [direct API](#direct-api) stays available to your code | `true` |

> Binding to `0.0.0.0` or `::` exposes the runtime control surface (click, drag, fill…) to your network. Use only on trusted networks.

### Direct API

Everything the WebSocket exposes is also callable directly on the `Locator` autoload, so you can drive the same behavior from your own scripts (debug overlays, in-game dev tools, custom test rigs) without bringing up a client. Combine with `GODOT_LOCATOR_SERVER_ENABLED=false` if you don't need the wire interface at all.

```gdscript
var yaml: String = Locator.snapshot()
Locator.click($Form/SubmitButton)
Locator.fill($Form/NameInput, "Sanito")
```

Currently exposed: `snapshot(depth, skip_invisible)`, `click(node)`, `double_click(node)`, `right_click(node)`, `fill(node, text)`. The locator chain (`get_by_*` / filter) is wire-only for now — call methods with a `Node` you already have.

### Snapshot

YAML-structured text snapshot of SceneTree. Only `Control` nodes are emitted; non-Control parents (`Window`, `CanvasLayer`, `Node2D`…) are walked through transparently so Controls nested under them still surface.

```yaml
- VBoxContainer [Form]:
  - Label [Title] "Welcome"
  - LineEdit [NameInput ref=e1] placeholder="Name" text=""
  - Button [SubmitButton ref=e2] "Submit" disabled
```

Each line is `- <Class> [<name>[ ref=eN]] [ "<text>"] [ <key>="<val>"]* [ <flag>]* [:]`. Refs (`eN`) are stable instance ids — once issued, they keep pointing at the same node for follow-up `locate`/control calls — and are off by default; pass `tag_ref: true` (Playwright-style) to have them emitted for interactive nodes (`LineEdit` / `TextEdit` / `BaseButton`) and any node implementing the custom-format hook below.

#### Options
| Name | Description | Default |
| ---- | ----------- | ------- |
| depth | maximum traversal depth from the root | 0 (all) |
| skip_invisible | omit nodes whose `visible` is false (and their subtrees) | true |
| tag_ref | emit `ref=eN` markers for interactive / custom-format nodes | false |

#### Custom node formatting

To extend the snapshot for your own node classes, implement `_godot_locator_format() -> Dictionary` (or `_GodotLocatorFormat()` from C#). Any node with this method auto-gets a ref.

```gdscript
class_name HealthBar extends Control

func _godot_locator_format() -> Dictionary:
    return {
        "text": "%d/%d" % [current, maximum],
        "attrs": {"pct": str(int(100.0 * current / maximum))},
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
        ["attrs"] = new Dictionary { ["pct"] = ((int)(100.0 * Current / Maximum)).ToString() },
        ["flags"] = Current < Maximum * 0.2 ? new Array { "critical" } : new Array(),
    };
}
```

Renders as:

```yaml
- HealthBar [Player ref=e7] "30/100" pct="30" critical
```

| Field | Effect |
| ----- | ------ |
| `text` | overrides the built-in positional `"…"` (Label/Button/RichTextLabel default) |
| `attrs` | merged after built-in attrs (e.g. LineEdit's `placeholder` / `text`) |
| `flags` | appended after built-in flags (e.g. BaseButton's `disabled`) |

All three keys are optional — return any subset.

**Class names** in the snapshot are resolved in this order: GDScript `class_name` (via `Script.get_global_name()`) → the project's global class registry (path lookup) → for `.cs` scripts, the filename basename → engine class (`get_class()`). The `.cs` step is a fallback because Godot 4.6's C# binding doesn't expose user class names to GDScript through either of the first two paths. Keep the standard C# convention of one `public partial class FooBar` per `FooBar.cs` and your custom node will appear as `FooBar` in the snapshot; otherwise it falls through to the engine base type (e.g. `Button`).

### Locate

| Name | Description | Scope |
| ---- | ----------- | ----- |
| get_by_name | locate by node name | - |
| get_by_class | locate by node class/subclass | - |
| get_by_text | locate by text | Label/Button/CheckBox/RichTextLabel |
| get_by_placeholder | locate by placeholder | LineEdit/TextEdit |
| get_by_group | locate by scene tree group membership | - |
| get_by_path | locate by `NodePath` relative to the current scope | - |

### Filter

| Name | Description |
| ---- | ----------- |
| has | keep matches containing a descendant that matches the inner locator |
| has_not | keep matches that do NOT contain a descendant matching the inner locator |
| has_text | keep matches whose text contains the given string (or matches a regex) |
| visible | keep only matches whose `visible` chain resolves to true |
| first | narrow to the first match |
| last | narrow to the last match |
| nth | narrow to the match at the given index |
| count | resolve to the number of matches |

### Control

Synthesize input on the located node. Each method asserts a single match (use a filter or `nth` to disambiguate).

| Name | Description | Scope |
| ---- | ----------- | ----- |
| click | left-click at the node's center | Control / Node2D |
| double_click | two left-clicks within the OS double-click window | Control / Node2D |
| right_click | right-click at the node's center | Control / Node2D |
| hover | move the mouse over the node | Control / Node2D |
| focus | call `grab_focus()` | Control |
| fill | replace `text` (clears, then types) | LineEdit / TextEdit |
| press_key | dispatch an `InputEventKey` (e.g. `"enter"`, `"ctrl+a"`) | focused node |
| drag_to | press on this node, motion to target locator, release | Control / Node2D |
| scroll | wheel-scroll by `dx`/`dy` ticks at the node's center | ScrollContainer / any |

## [Tests](tests/)

Integration tests launch a headless Godot per test, drive it over WebSocket, and assert against snapshots / observable state.

```sh
tests/run.sh              # all tests
tests/run.sh -k snapshot  # forward args to pytest
```

Requires `godot` on PATH (or `GODOT_BIN=/path/to/godot`) and [`uv`](https://docs.astral.sh/uv/). Test projects live under `tests/projects/<name>/`; each is a real Godot project with `addons/godot-locator` symlinked back to this repo.

## [MCP](mcp/)


