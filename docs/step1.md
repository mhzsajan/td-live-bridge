# Step 1 — the pipe (proven)

Smallest testable build: one persistent socket, one channel, proved end-to-end.

**Result: Ableton's tempo appears as a CHOP channel in TouchDesigner.**

---

## The proof

Tempo changed in Ableton, TD's channel followed every time (<3 s):

| Ableton BPM | TD `Tempo` channel |
|---|---|
| 120 | 120.0 |
| 133 | **133.0** |
| 120 | 120.0 |
| 144 | **144.0** |
| 120 | 120.0 (restored) |

The 120 ↔ 144 step matters: `Tempo: 120.0` alone was **indistinguishable
from my own initialised default**. Only a value I didn't choose proved the
link.

---

## The network

```
/project1/base_live_bridge        (baseCOMP, display=true)

  LiveBridgeExt      textDAT   file-synced extension source
  pump_exec          executeDAT  frame start → Pump()
        │
        ▼
  par_live       parameterCHOP  →  null_live  nullCHOP  →  out1  outCHOP
                    outputs: Tempo, Connected
```

Positions: DATs at X=-200, main chain on Y=0, 175 px spacing.

```
LiveBridgeExt (-200, 0)   pump_exec (-200, -125)
                                  par_live (0, 0) → null_live (175, 0) → out1 (350, 0)
```

---

## `base_live_bridge` parameters

**Extensions page**

```
ext0object  = op('./LiveBridgeExt').module.LiveBridgeExt(me)
ext0promote = true
ext0name    = (empty)
```

> **Promotion is FLAT.** With `ext0promote=true` and empty `ext0name`, members
> land directly on the COMP: `op('base_live_bridge').Pump`, `.LiveTempo`.
> Accessing `c.LiveBridgeExt` raises `tdAttributeError` — there is no nested
> class-name object.

**Custom page `Live`**

| Par | Type | Value / expression |
|---|---|---|
| `Connect` | Toggle | `true` — user control, defaults on |
| `Rate` | Float | `10` (Hz) |
| `Tempo` | Float | expr `me.LiveTempo` |
| `Status` | Str | expr `me.LiveStatus` → `"connected"` |
| `Connected` | Toggle | expr `1 if me.LiveStatus == 'connected' else 0` |

**Common page:** `display = true` (a flag — see gotchas).

`Tempo`, `Status`, `Connected` show `mode: ParMode.EXPRESSION`.

---

## `pump_exec` (executeDAT)

```
active     = true
framestart = true
language   = python
```

Body:

```python
def onFrameStart(frame):
	op('..').Pump()
```

---

## `par_live` (parameterCHOP)

```
ops        = ..
custom     = true
builtin    = false
parameter  = Tempo Connected     ← the filter (NOT scope)
```

Output is **exactly two channels**: `Tempo`, `Connected`.

---

## The extension

Source of truth in this repo: [`../bridge/LiveBridgeExt.py`](../bridge/LiveBridgeExt.py)

TouchDesigner loads it file-synced from:

```
C:\Users\Admin\Desktop\code\py\base_live_bridge\LiveBridgeExt.py
```

### Design decisions and why

| Decision | Reason |
|---|---|
| **No background thread** | TD is not thread-safe; `executeDAT` callbacks run on the main thread. |
| **`select()` with zero timeout** | The skill warns execute DATs block the cook loop. Nothing here blocks. |
| **One socket, held open** | A fresh connect flashes `Client connected` in Live's status bar every poll. |
| **`TDF.createProperty(dependable=True)`** | A plain `self.x = …` does not trigger downstream recooks — the channel would freeze. |
| **Bytes rebind, not slice-delete** | `bytes` is immutable; `del buf[:n]` raises. |
| **Guarded `create_connection`** | The one blocking call — only attempted when not already connected. Loopback refuses fast when Live is closed. |

### Structure

```python
class LiveBridgeExt:
    HOST, PORT = '127.0.0.1', 9877
    COMMAND = 'get_song_transport'

    Pump(self)        # per-frame: schedule → Flush → Drain, never blocks
    TryConnect(self)  # only when self.sock is None
    Flush(self)       # select(0) write of pending request bytes
    Drain(self)       # select(0) read, split on \n, HandleLine each
    HandleLine(self)  # json.loads → guard status → set LiveTempo
    HandleError(self) # record + drop connection
```

Read-only state: `LiveTempo` (float), `LiveStatus` (str), `lastError`.

---

## Verification performed

| Check | Result |
|---|---|
| `get_errors` | **0** |
| Signal flow | no cycles, no orphans; `par_live → null_live → out1` |
| Extension bound | 9 methods promoted, `className: LiveBridgeExt` |
| Channels | exactly `Tempo`, `Connected` |
| Cook cost | max **0.033 ms** — 0.0% of frame budget |
| End-to-end | 120 → 144 → 120, TD followed each time |
| Saved | `C:\Users\Admin\Desktop\NewProject.1.toe` |

---

## Four bugs the review caught

1. **The pump was dead on arrival.** `set_dat_content` has **no `values`
   field** — it took my `text` and silently dropped `framestart`, so the
   callback never fired. Caught only because `get_parameters` showed
   `framestart: false`.

2. **A dead `Status` channel.** A `Str` custom par flattens to a permanent
   `0.0` — actively misleading in a visuals context. Replaced with a `Connected`
   Toggle.

3. **`scope` is a trap.** It looks like the channel filter but is hardcoded
   disabled (`enableExpr = None`). The real filter is the **`parameter`**
   StrMenu (default `*`, space-separated names).

4. **`display` is a flag, not a parameter.** `set_parameters` errors
   `parameter_not_found`; `edit_operator` owns flags.

Full list: [td-gotchas.md](td-gotchas.md).
