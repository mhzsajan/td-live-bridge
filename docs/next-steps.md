# Next steps

Where to resume, in order. Step 1 is done and saved.

---

## Resume checklist

1. **Open the TD project:** `C:\Users\Admin\Desktop\NewProject.1.toe`
   (Step 1 saved to `NewProject.1.toe` — check for `NewProject.2.toe` if TD
   auto-versioned on save.)
2. **Confirm the pipe is alive:**
   ```bash
   uv run python tools/tdmcp_probe.py inspect_values "@<path-to-channels-args>"
   # expect: {"Tempo": 120.0, "Connected": 1.0}
   ```
   Or read the `Connected` par on `/project1/base_live_bridge`.
3. **Optional:** restart OpenCode so `mcp.touchdesigner` becomes native tools
   (config was read at startup; the raw harness works meanwhile).

---

## Step 2 — more channels (next)

Extend the poller beyond `get_song_transport` to expose what the set is
*doing*, not just its tempo.

**Commands to add** (all verified as wire commands):
- `get_playing_clips` → which clips are firing
- `get_track_meters` → per-track levels

**Target channels:**

```
live/tempo                    ← DONE (step 1)
live/playing                  0|1  transport
live/beat                     position in beats → animation phase
live/sig_num  / sig_den
live/rec                      0|1
live/track_<n>_meter  L/R
live/track_<n>_playing_slot   which clip is live
live/fired_slot               pre-trigger, for anticipatory visuals
```

### ⚠️ Must verify first

**`get_track_meters` returned a single flat dict** for the 1-track session —
not a list. The MCP server's own code (`doctor.py:294`) hints a `{"tracks": [...]}`
shape may exist:

```python
"meters": meters.get("tracks", meters) if isinstance(meters, dict) else meters
```

**Query a set with 2+ tracks before designing the channel naming.** Do not
build against an assumption — that habit is what caught the four Step 1 bugs.

Design notes: [step1.md](step1.md), [wire-protocol.md](wire-protocol.md).

---

## Step 3 — Link CHOP (needs your hands)

Ableton Link gives beat-locked tempo/phase with no custom code — the cleanest
path to animation that stays locked to the set.

**This requires you:** enable **Show Link Toggle** in Ableton Live's
Preferences → Link/Tempo/MIDI, then switch **Link** on.

Once available, TD's Link CHOP provides tempo and phase directly — likely
better than polling `current_time` for beat position.

---

## Step 4 — TD → Live (optional)

UDP **9882**, inbound only, **no replies**. For firing clips and changing tempo
from visuals.

Design it as **one-way intent** — the socket cannot acknowledge, so don't build
a request/response protocol on it.

---

## Housekeeping

- **Report upstream?** No. The `get_parameters` "bug" was my error —
  documented `include_defaults` behaviour. Nothing to report.
- **Skills check:** `Agentskillsstatus` should read `Installed v1.4.0 (19 skills)`.
  If it regresses, re-pulse `Installagentskills`.
- **Extension edits:** edit
  `C:\Users\Admin\Desktop\code\py\base_live_bridge\LiveBridgeExt.py` directly —
  the DAT is file-synced and reloads on save. Then commit the same change to
  `bridge/LiveBridgeExt.py` here.
- **Tempo** is at 120 BPM (its original value — testing moved it to 133 and
  144, both restored).

---

## Open questions

1. Multi-track `get_track_meters` shape (see Step 2).
2. Does `current_time` give reliable beat position, or is Link CHOP strictly
   better for phase? Worth comparing before committing to one.
3. Should visuals freeze when `Connected` drops to 0? Currently nothing
   consumes that channel yet — it's exposed but unused.
