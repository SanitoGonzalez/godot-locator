---
sidebar_position: 4
---

# Assert & Eval

`assert` and `wait` turn a session into a test runner: they check a condition against the live SceneTree and exit `0` on pass, `1` on fail — so an agent (or a shell script) can branch on the result. `eval` is the escape hatch for reading game state a matcher cannot express.


## Asserting Conditions

```sh
godot-locator-cli assert <target> <matcher> [value...] [--timeout <seconds>]
```

`assert` re-resolves `TARGET` and re-checks the matcher **every frame** until it passes or the timeout elapses (default `5s`). Because it polls, you do not need a separate wait step for animations, scene transitions, timers, or anything else that resolves over several frames — the assertion simply waits it out.

`TARGET` is a ref or selector, exactly as in [Interaction](./interaction.md#targeting-nodes). Unlike interactions, assertions do not require a unique match — matchers like `count` are defined over the whole match set, and `visible`/`text` pass if **any** match satisfies them.

On failure the command prints a `FAIL` line with what it observed, followed by the current snapshot so you can see why, then exits `1`:

```
FAIL  #GameOver visible  (observed: false, waited 5000ms)
### Snapshot
...
```


### Matchers

| Matcher | Passes when |
| ------- | ----------- |
| `visible` | A match exists and is visible in the tree |
| `hidden` | No match is visible (an absent node counts as hidden) |
| `exists` | At least one node matches |
| `absent` | No node matches |
| `text <s>` | A match's displayed text equals `<s>` |
| `contains <s>` | A match's displayed text contains `<s>` |
| `value <s>` | A `LineEdit`/`TextEdit`/`Range`/`OptionButton` value equals `<s>` |
| `checked` / `unchecked` | A toggle-mode button is pressed / not pressed |
| `enabled` / `disabled` | A button is enabled / disabled |
| `count <n>` | Exactly `<n>` nodes match |
| `property <key> <value>` | A match's `<key>` property equals `<value>` |
| `expr <gdscript>` | A GDScript expression evaluates truthy (see below) |

Options: `--timeout <seconds>` sets how long to keep polling; `--json` emits the raw result (including `pass`, `observed`, `waited_ms`, and the `snapshot`).


### `wait`

`wait` is `assert` with a longer default timeout (`10s`) and a default matcher of `visible`:

```sh
godot-locator-cli wait "#LevelComplete"            # wait until visible
godot-locator-cli wait "/root/Game" exists         # wait until the node appears
godot-locator-cli wait "#Score" text "100" --timeout 15
```


## Evaluating Expressions

When no matcher fits, `eval` runs a single GDScript expression inside the running game and prints the result:

```sh
godot-locator-cli eval <expression> [--ref <target>]
```

With `--ref`, the targeted node is exposed to the expression as the local variable `node`. The `expr` matcher above is the assertable form of the same mechanism — `TARGET` binds as `node` (pass `-` to bind nothing).

`eval` and `expr` have full access to game state, so they are gated: set `GODOT_LOCATOR_EVAL_ENABLED=true` on the **game** process to enable them. The expression is GDScript syntax — on C# projects use `node.get_name()`, not `node.GetName()` — and must be a single expression (no `var`, `func`, or multiple statements).

```sh
godot-locator-cli eval "Engine.get_frames_per_second()"
godot-locator-cli eval "node.text.length()" --ref "#NameInput"
godot-locator-cli assert "/root/Game/Player" expr "node.health > 0"
godot-locator-cli assert - expr "Score.total >= 100"   # no node bound
```


## A Test Flow

Each line is one command; the script stops at the first failure because every `assert` exits non-zero on fail.

```sh
godot-locator-cli launch ./my-game
godot-locator-cli assert "#MainMenu" visible
godot-locator-cli click "#StartButton"
godot-locator-cli assert "/root/Game" exists --timeout 5    # waits out the scene change
godot-locator-cli assert "Label#Score" text "0"
godot-locator-cli action move_right hold
godot-locator-cli assert "/root/Game/Player" expr "node.position.x > 100" --timeout 3
godot-locator-cli screenshot --filename level1.png
godot-locator-cli terminate
```
