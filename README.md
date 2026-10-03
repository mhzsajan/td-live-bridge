# td-live-bridge

TouchDesigner ↔ Ableton Live, driven by OpenCode.

Live's tempo, transport, clips and meters exposed as **CHOP channels** inside
TouchDesigner, so visuals can react to the set in real time — and OpenCode can
author those networks over MCP.

**Status: Step 1 proven end-to-end.** Ableton's tempo flows into a TD CHOP
channel, verified by changing BPM in Live and watching TD follow.

```
Ableton set_tempo(144) → TCP 9877 → TD frame-start pump
                       → dependable property → expr par → CHOP "Tempo" = 144.0
```

---

## Why this repo exists

Two systems were already talking (AbleBridgePlus → Ableton Live, and
TouchDesigner → OpenCode via TDMCP), but nothing connected TouchDesigner to
Live. This closes that gap.

It also captures everything **measured** along the way, so the next session
starts from evidence instead of re-deriving it.

---

## Read these first

| Doc | What's in it |
|---|---|
| [docs/setup.md](docs/setup.md) | Reproduce the environment — config, skills, ports |
| [docs/findings.md](docs/findings.md) | The capability audit — what was measured, with evidence |
| [docs/architecture.md](docs/architecture.md) | The decision that shaped everything: build time vs run time |
| [docs/wire-protocol.md](docs/wire-protocol.md) | AbleBridgePlus TCP 9877, verified live |
| [docs/step1.md](docs/step1.md) | The build that works — network, parameters, proof |
| [docs/td-gotchas.md](docs/td-gotchas.md) | TD API traps hit during the build (read before building) |
| [docs/next-steps.md](docs/next-steps.md) | Where to resume |

---

## Layout

```
bridge/LiveBridgeExt.py   the extension: persistent non-blocking socket to :9877
tools/                    probe harness (imports tdmcp_probe; keep together)
docs/                     findings, protocol, gotchas, roadmap
examples/                 argument files for the probe harness
```

The extension lives in the repo as source of truth. TouchDesigner loads its
copy from `C:\Users\Admin\Desktop\code\py\base_live_bridge\LiveBridgeExt.py`
(file-synced DAT) — re-copy after editing, or edit that file directly and the
DAT reloads on save.

---

## The three pieces of the stack

```
┌─────────────────────┐   TCP 9877    ┌──────────────────────┐
│    Ableton Live     │◄─────────────►│   AbleBridgePlus     │
│  (Remote Script)    │  JSON / line  │  475-tool MCP server │
└─────────────────────┘               └──────────────────────┘
                                                   ▲
                                          TCP 9877 │  (this repo)
                                                   │
┌─────────────────────┐   MCP 13316   ┌──────────────────────┐
│      OpenCode       │◄─────────────►│   TouchDesigner      │
│  (authors networks) │   JSON-RPC    │  TDMCP + base_live_  │
└─────────────────────┘               │  bridge (runtime)    │
                                      └──────────────────────┘
```

**OpenCode authors the network. The network then runs on its own** — no MCP
in the loop at 60 fps. See [docs/architecture.md](docs/architecture.md).

---

## Requirements

- Ableton Live 12 (tested 12.4.2) with **AbleBridgePlus** installed
- TouchDesigner (tested 2025.33230)
- **TDMCP** 1.1.55 (official `TouchDesigner/TDMCP`)
- OpenCode with `mcp.touchdesigner` configured

Full setup: [docs/setup.md](docs/setup.md).

---

## Proven, not assumed

Every claim in these docs was measured on this machine. Where an assumption
turned out wrong, the doc says so — including two of mine that were:

- `get_parameters` is **not** buggy (it's documented `include_defaults` behaviour)
- TDMCP needed **no** new development (its ceiling is `execute_code` = Python)

See [docs/findings.md](docs/findings.md).
