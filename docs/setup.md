# Environment setup

How to reproduce this stack on a fresh machine. Every step here was performed
and verified on Windows, Live 12.4.2, TD 2025.33230.

---

## 1. Ableton Live: AbleBridgePlus

Install the remote script and select it in Live's Preferences → Link/Tempo/MIDI
→ Control Surface.

The installed folder name is **versioned**:

```
AbleBridgePlus_0_8_0
```

Underscores, not dots — Python splits module names on `.` and a dotted folder
name breaks import. This was verified live on Live 12's Python 3.11.

> **After every upgrade you must re-select the Control Surface slot.**
> `Preferences.cfg` is a binary blob and cannot be pre-patched. One
> re-selection per upgrade is the accepted cost of having the version visible.

On startup Live's status bar reads:

```
AbleBridgePlus v0.8.0 ready - TCP 9877 / UDP 9882
```

and `Log.txt` shows:

```
MidiRemoteScript 3 [Control Surface="AbleBridgePlus_0_8_0" Input="None" Output="None"]
AbleBridgePlus v0.8.0 initialized
```

Repo: [`mhzsajan/AbleBridgePlus`](https://github.com/mhzsajan/AbleBridgePlus)

---

## 2. Ports

| Port | Protocol | Direction | Used by |
|---|---|---|---|
| **9877** | TCP, JSON per line | bidirectional, request/response | AbleBridgePlus ← MCP server, ← TD poller |
| **9882** | UDP, JSON | **inbound only, no replies** | TD → Live writes only |
| 9878 / 9879 | OSC | — | M4L bridge (unused here) |
| 9880 | HTTP | — | web dashboard (unused here) |
| **13316** | HTTP, MCP streamable | TD → OpenCode | TDMCP |

**TCP 9877 is threaded per client** — TD polling coexists with the MCP server
without conflict.

⚠️ **Keep TD's socket persistent.** Every *new* connection to 9877 fires a
`Client connected` message in Live's status bar. A poller that reconnects per
poll will spam it. This is why the extension holds one socket open.

> **UDP 9882 is fire-and-forget with no reply channel.** TD → Live writes only;
> there is no way to get an acknowledgement or read state back over it. Reads
> must go over TCP 9877. TDAbleton and M4L were ruled out — no Max on this PC.

---

## 3. TouchDesigner: TDMCP

Use the official **`TouchDesigner/TDMCP`** (1.1.55), not a community
alternative. It runs inside TD, speaks streamable-HTTP, explicitly supports
OpenCode, and `execute_code` removes any capability gap.

Drop `TDMCP.tox` into the network, go up (`u`), open the MCP page, set
**Active**. Verify the checksum against the published `TDMCP.json` before
loading — this was done (`sha256 …c9d4`).

### TDMCP parameter settings applied

| Page | Parameter | Value | Why |
|---|---|---|---|
| MCP | `Installfor` | **`opencode2`** | see below |
| MCP | `Installscope` | **`user`** | see below |
| MCP | `Active` | `true` | serves on 13316 |
| MCP | `Port` | `13316` | |
| MCP | `Addressscope` | `localhost` | **leave it — see security** |
| MCP | `Auth` | `false` | localhost only |
| MCP | `Usehttps` | `false` | localhost only |
| Tune | `Inlineimages` | **`on`** | `view_operator` returns base64 inline |
| Tune | `Ratelimiting` | on (5 s threshold, 1 s cooldown) | never fired in testing |

**Do not add `codemode`** to the MCP config entry — the official schema's
remote entry is `additionalProperties: false`.

### Why `opencode2`, not `opencode`

Proven by loading the `memory` skill: its base directory is
`~\.config\opencode\skills\memory`, so this client **does** read
`~/.config/opencode/skills/`. That's v2's user-scope destination. TDMCP's own
table says v1 has "no skills mechanism… connection only".

Corroborated by the Code Mode `execute`/`search` catalog this session runs on —
v2's default.

### Why `Installscope` = `user`, not `project`

The TD project's folder is **Desktop** (`NewProject.1.toe` lives there).
Project scope would have written skills to `Desktop\.agents\skills\`, which
**no session reads**. User scope writes to `~/.config/opencode/skills/`.

### Skills

Pulsing `Installagentskills` installed **v1.4.0 — 19 `td-*` skills**, live, no
restart needed. They appear in-session immediately.

Verify: `Agentskillsstatus` → `Installed v1.4.0 (19 skills)`.

These skills immediately caught real errors — `td-general` says *"Never
`absTime.seconds` — overflows, use `lfoCHOP` or `timer`"*, which is exactly
what an earlier proof expression had used.

---

## 4. OpenCode config

`C:\Users\Admin\.config\opencode\opencode.jsonc`:

```jsonc
"mcp": {
  "touchdesigner": {
    "type": "remote",
    "url": "http://127.0.0.1:13316/mcp",
    "enabled": true,
    "oauth": false,
    "timeout": 30000
  }
}
```

**The flat `mcp.<name>` shape is correct.** TDMCP's `Removemcp` field points at
`mcp.servers` (v2's nested shape), but flat demonstrably works: `ablebridge` is
configured the identical flat way and its 475 tools loaded in-session.

Config is read at **startup** — OpenCode must be restarted for
`mcp.touchdesigner` to become native tools.

### Security

- Use `127.0.0.1`, **never `localhost`** — IPv6 `::1` causes a connection refusal.
- Leave **Server Address Scope = Localhost only**. `execute_code` is
  shell-equivalent: it wrote a file straight into this machine's temp
  directory during testing.

---

## 5. Probe harness

The raw MCP harness works even when native tools aren't loaded (i.e. before an
OpenCode restart).

```bash
# list all 26 tools
uv run python tools/tdmcp_probe.py

# dump a tool's input schema — never guess parameters
uv run python tools/tdmcp_probe.py --schema set_parameters

# call a tool, args from a file
uv run python tools/tdmcp_probe.py get_errors '{}'
uv run python tools/tdmcp_probe.py build_network "@examples/build_internals.json"
```

> **`@file` arguments are required for structured input.** PowerShell strips
> embedded quotes from command-line JSON. Write args to a file.

Capture a TOP to PNG:

```bash
uv run python tools/td_view.py /project1/proof_out out.png low
```
