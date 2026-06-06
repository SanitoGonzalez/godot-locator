---
sidebar_position: 3
---

# Interaction

Interaction commands synthesize real input events — mouse clicks, key presses, drags, input actions — into the running game, exactly as Godot would receive them from a player. Each command targets a node, performs the action, and returns the updated SceneTree so you can see the result without a separate `snapshot` call.


## Targeting Nodes

Every command that acts on a node takes a `TARGET` — either a **ref** or a **selector**.

**Refs** (`e5`, `e12`) are stable handles handed out by `snapshot`. Each points at one specific node and stays valid until that node is freed. Use a ref when you have just read a snapshot and want to act on the exact node you saw — it is unambiguous and never matches the wrong thing.

**Selectors** are queries, re-resolved every time the command runs. Use a selector for readable scripts, or when you need to target a node you have not snapshotted yet (for example while waiting for it to appear).

| Selector | Matches |
| -------- | ------- |
| `/root/Main/Menu/Start` | An absolute `NodePath` from the scene root |
| `#Start` | A node by name |
| `Button` | A node by class (`get_class()` or the script's `class_name`) |
| `Button#Start` | Class **and** name together |
| `Label:text("Score")` | Filter matches by their displayed text (exact) |
| `Button:nth(0)` | Keep only the *i*-th match (0-based) |

Interaction commands require a selector to resolve to **exactly one** node. If it matches several, the command fails and tells you how many it hit — narrow the selector (add a class or `:nth(i)`) or use a ref instead.

```sh
godot-locator-cli click e5                 # by ref
godot-locator-cli click "#StartButton"     # by name
godot-locator-cli click "Button#Start"     # by class + name
godot-locator-cli fill "#NameInput" Alice  # selectors work anywhere a TARGET is taken
```


## How It Works

After the input is delivered, the command advances the game one frame before reading the SceneTree back. This means effects Godot defers past the current frame — `change_scene_to_file`, `queue_free`, `call_deferred` — are reflected in the snapshot you get back, not just synchronous reactions.

By default the updated snapshot is printed under a `### Snapshot` block. Pass `--no-snapshot` to suppress it, or `--json` to get the raw response.


## Commands

| Command | Description |
| ------- | ----------- |
| `click <target> [left\|right\|middle]` | Click a node (button defaults to `left`) |
| `dblclick <target> [button]` | Double-click a node |
| `hover <target>` | Move the mouse over a node (hover styling, tooltips, `mouse_entered`) |
| `fill <target> <text>` | Replace the text of a `LineEdit`/`TextEdit` (atomic) |
| `check <target>` | Set a toggle-mode button to checked |
| `uncheck <target>` | Set a toggle-mode button to unchecked |
| `select <target> <value>` | Select an `OptionButton` item by index or label |
| `type <text>` | Type into the currently focused Control (per-character key events) |
| `press <key>` | Press + release a single key (`enter`, `escape`, `arrowleft`, `f1`, `a`) |
| `keydown <key>` / `keyup <key>` | Hold a key down / release it across frames |
| `action <name> [tap\|hold\|release]` | Drive a Godot input action by name (mode defaults to `tap`) |
| `mousemove <x> <y>` | Move the cursor to viewport coordinates |
| `mousedown [button]` / `mouseup [button]` | Press / release a mouse button at the cursor |
| `mousewheel <dx> <dy> [--ref <target>]` | Scroll the wheel (tick counts; positive = right/down) |
| `drag <from> <to> [button]` | Drag from one node to another |
| `resize <width> <height>` | Resize the game window |

Common options: `--no-snapshot` suppresses the snapshot block, `--json` emits the raw response.


## Keys, Actions, and Text

There are three ways to send input, in increasing order of game-awareness:

- **`press` / `type`** synthesize raw keyboard events. Use `type` to enter text into a focused field character by character, and `press` for individual keys like `enter` or `escape`. For replacing a field's whole value, prefer `fill` — it is atomic and does not depend on focus.
- **`keydown` / `keyup`** hold a key across multiple frames — useful for testing sustained movement or autorepeat.
- **`action`** drives a registered entry from **Project Settings → Input Map** by name, so it respects whatever keyboard/gamepad bindings the player would use. This is the closest match to real gameplay input. `tap` presses then releases, `hold` leaves it held, `release` releases a held action.


## Examples

```sh
# Fill a form and submit it
godot-locator-cli fill "#NameInput" "Alice"
godot-locator-cli fill "#EmailInput" "alice@example.com"
godot-locator-cli click "#SubmitButton"

# Drive gameplay with input actions, holding a movement key
godot-locator-cli action move_right hold
godot-locator-cli action jump tap
godot-locator-cli action move_right release

# Drag one node onto another
godot-locator-cli drag "#Card1" "#DropZone"

# Scroll a list, suppress the snapshot to keep output terse
godot-locator-cli mousewheel 0 3 --ref "#ScrollContainer" --no-snapshot
```
