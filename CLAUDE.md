# Godot Locator

## Comment style

Default to **no comments**. Add one only when the WHY is non-obvious — a
hidden constraint, a subtle invariant, a workaround, or surprising behavior.

Don't write:
- What the code does (names handle that).
- References to callers, tasks, or future work ("used by X", "lives here so
  MCP can reuse", "added for the launch flow").
- Spec restatements or architectural justifications inside modules.
- Multi-paragraph docstrings or banner comments.

Module docstrings: one short paragraph. No bullet lists of internals, no
cross-package references.

When in doubt, delete it.
