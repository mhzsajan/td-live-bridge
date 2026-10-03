# TouchDesigner API gotchas

Hit while building Step 1. **Read `--schema <tool>` before every call** — three
of these were schema-shaped, not logic-shaped.

---

## Tools

### `set_dat_content` has no `values` field

```jsonc
// ❌ silently drops everything except `text`
{"path": "/project1/x", "text": "…", "values": {"framestart": true}}
```

Its schema accepts `path`, `text`, `rows`, `file_content`, `file_type`,
`file_path`, `old_string`, `new_string`, `replace_all`. **`values` is not among
them** — and it fails *silently*, returning only `{"length": N}`.

This left the frame pump dead while the network reported 0 errors. Set toggles
with **`set_parameters`**, separately.

### `display` is a flag, not a parameter

```jsonc
// ❌ {"error": "Parameter not found: "display"", "code": "parameter_not_found"}
{"path": "/project1/x", "values": {"display": true}}
```

Flags (`display`, `render`, `viewer`, `bypass`, `lock`, `cloneImmune`,
`allowCooking`) belong to **`edit_operator`**:

```jsonc
{"path": "/project1/base_live_bridge", "display": true}
```

`edit_operator` also handles `rename`, `copy_to`, `move_to`, `change_type`,
`nodeX/nodeY`, `color`.

### `reposition_operators` is the move tool

```jsonc
{"parent_path": "/project1/base_live_bridge",
 "positions": {"LiveBridgeExt": [-200, 0], "par_live": [0, 0]}}
```

Not discoverable via OpenCode's `search()` — TDMCP's 26 tools load at OpenCode
startup, so they aren't in the index. List them:

```bash
uv run python tools/tdmcp_probe.py        # no args → all 26
```

### `get_parameters` — filter gotchas

- **Defaults hidden unless asked.** `include_defaults: true` → `count: 71`.
  Without it you get non-defaults only. *Documented behaviour, not a bug.*
- **`names` is case-sensitive.** `Active` matches nothing; `active` matches.
  Use `get_help` for the real casing — it returns lowercase (`active`,
  `framestart`, `executeloc`).
- Menu-valued pars take the **menuName**, not the label:
  `{"Inlineimages": "on"}`, `{"Installfor": "opencode2"}`.

### `parameterCHOP` — `scope` is a trap

`scope` *looks* like the channel filter but is **hardcoded disabled**
(`enable = False`, `enableExpr = None` — confirmed by reading the par).

The real filter is the **`parameter`** StrMenu:

```jsonc
{"path": "/project1/base_live_bridge/par_live",
 "values": {"parameter": "Tempo Connected"}}
```

Default `*` (all), space-separated names. Setting it took the output from
4 channels to exactly 2.

Other useful `parameterCHOP` pars: `custom` (fetch custom pars), `builtin`,
`renamefrom` / `renameto`, `timeslice` (also disabled).

### `pulse_parameter` needs `{path, parameter}`

```jsonc
{"path": "/project1/TDMCP", "parameter": "Installagentskills"}
```

### `get_help` takes operator types, not tool names

```jsonc
{"types": ["parameterCHOP"]}   // ✅  → 16 parameters with labels
{"types": ["get_parameters"]}  // ❌  → nothing
```

Ops are **suffixed**: `noiseTOP`, `parameterCHOP`, `executeDAT` — not `noise`.

---

## Python in TD

### Never `absTime.seconds`

Overflows. Use `lfoCHOP` or `timer`. (`td-general` caught this — an early proof
expression used `math.sin(absTime.seconds)`.)

### `math.sin`, not `sin`

Bare `sin` → `NameError`, which blanks the TOP.

### `bytes` is immutable

```python
del buf[:n]      # ❌ TypeError
buf = buf[n:]    # ✅ rebind
```

### Extensions: promotion is FLAT

`ext0promote = true` + `ext0name` empty → members land **directly on the COMP**:

```python
op('base_live_bridge').Pump        # ✅ bound method
op('base_live_bridge').LiveTempo   # ✅ 120.0
op('base_live_bridge').LiveBridgeExt   # ❌ tdAttributeError
```

Probe each path separately — a combined `hasattr` probe masks *which* access
failed, and `dir()` on a TD COMP lies (it resolves via `__getattr__`).

### State needs `TDF.createProperty(dependable=True)`

A plain `self.x = …` does **not** trigger downstream recooks. Without
`dependable=True` the channel freezes even though the extension is working.

### Name collisions: par vs promoted member

A `Tempo` custom par + a promoted `Tempo` property makes the expression
circular. Keep them distinct — par `Tempo`, property `LiveTempo`.

### `Str` pars become dead channels

`parameterCHOP` flattens a `Str` custom par to a permanent `0.0`. Use a `Toggle`
expressed from the string, or filter it out with `parameter`.

---

## Execution

- **execute DATs run on the main thread.** No HTTP, no heavy compute, no
  blocking sockets. `select()` with zero timeout is safe.
- **Silently-inert execute DATs.** An empty source par means no callbacks fire
  *and no error*. Check `active` / `framestart` explicitly with
  `get_parameters` — don't assume your write applied.

---

## Workflow traps

- **PowerShell strips embedded quotes** from command-line JSON. Always pass
  structured args via `"@file.json"`.
- **PowerShell `-replace` is case-insensitive**; double-quoted here-strings
  expand `$defs`.
- **`npm` is blocked** by execution policy on this machine
  (`UnauthorizedAccess` on `npm.ps1`).
- **My own regex on output can lie.** Two "no matches" results were patterns
  written against unescaped JSON while the response had escaped quotes
  (`\"page\"`). Check the raw string length before trusting a negative.

---

## Review discipline that caught real bugs

From `td-review-network`, and it worked:

1. `get_errors` — blocking, can't pass with errors
2. `list_operators` + `get_connections(graph=true)` — overlaps, orphans, cycles
3. `get_parameters` on key ops — expressions, extension wiring
4. `inspect_values` — runtime values
5. `get_cook_performance` — bottlenecks
6. Output check

**The key habit: a plausible number is not proof.** `Tempo: 120.0` was exactly
what my own default would produce. Only an input I didn't choose (BPM → 144)
proved the pipe.
