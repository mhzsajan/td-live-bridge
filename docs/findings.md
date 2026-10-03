# Findings — measured, not assumed

Every claim below was probed on this machine. Two of my own earlier claims were
wrong; both corrections are recorded here rather than quietly dropped.

---

## The question that started it

> *"Do we need to develop the MCP server for TouchDesigner further and make it
> more advanced so that you can work easily?"*

**Answer: no.** Don't rebuild it. Here's the evidence.

---

## Capability probes

| Probe | Result | Consequence |
|---|---|---|
| `execute_code` → Python + **filesystem write** | ✅ wrote `td_write_probe.txt` into *my* temp dir | **No capability ceiling.** Anything TD can do, I can do. |
| Rate limiter, 12 rapid calls | **0/12 throttled**, 17–33 ms each | Not a constraint — only fires after a >5 s call |
| `get_parameters` | `count: 71` with `include_defaults` | Works fine (see correction below) |
| `resources/list` | `[]` | No bundled resources |
| `prompts/list` | `Method not found` | No prompt templates |
| `resources/templates/list` | `[]` | No templates |
| **`resources.subscribe`** | **`false`** | **The server can never push to me — every read is a poll** |

### Server capabilities (verbatim)

```json
{
  "tools":     { "listChanged": false },
  "resources": { "subscribe": false, "listChanged": false }
}
```

No `logging`, `completions`, `prompts`, `roots`, or `sampling`.
Pure-tools server.

---

## Corrections (my own errors)

### 1. `get_parameters` is not buggy

I claimed it hid `Port`, `Auth`, `Installfor` and the whole Tune page. **Wrong
twice over:**

- The default behaviour is *documented* in the schema: *"Returns non-default
  params by default; use `names` for specific params, `pattern` for glob
  matching, `include_defaults` for all."*
- `include_defaults: true` **does** work — returns `count: 71` with every page
  present (`About`, `Common`, `Docs`, `Extensions`, `MCP`, `Skills`, `Tune`) and
  every parameter I thought was missing (`Port`, `Auth`, `Installfor`,
  `Inlineimages`, `Addressscope`, `Yolomode`, `Ratelimiting`, `Servername`,
  `Installagentskills`, `Agentskillsstatus`, `Usehttps`, `Certsdir`).

An earlier `include_defaults` attempt *looked* like it failed only because my
probe truncated responses at 3000 chars, cutting off `count` and the tail.

**Do not report this upstream.**

### 2. No custom TD MCP is needed

`execute_code` is arbitrary Python with filesystem access — the same ceiling a
bespoke server would have. Building our own would reimplement working tools to
reach an identical endpoint, then inherit the maintenance.

TDMCP is also under a Shared Use License: modify for your own projects, don't
redistribute it as a product.

---

## What actually *was* missing

Ranked by what blocks the goal (stunning visuals synced to the set):

| # | Gap | Fix | Cost |
|---|---|---|---|
| 1 | **No `td-*` skills installed** → six naming errors in one session | `Installagentskills` pulse | 2 min, zero code |
| 2 | `Installfor=claude`, `Inlineimages=False` | two settings | 2 min |
| 3 | **No Live↔TD data.** TDMCP structurally cannot know Ableton exists | *this repo* | the actual work |

---

## Why more MCP tools would not help

**MCP round trip = 17–33 ms. A 60 fps frame budget = 16.7 ms.**

One MCP call already costs an entire frame before any rendering. And a
language model's turn takes seconds. So I cannot drive visuals *through* MCP —
not because the tools are weak, but because of the arithmetic.

That forces the layer split:

```
BUILD TIME (MCP)                    RUN TIME (TD-internal)
create, wire, set params            CHOP Execute, polling loops,
read errors, screenshots            expressions, Link CHOP
→ OpenCode works here               → runs at 60 fps, needs no MCP
```

**MCP is for *authoring* networks. The network must then run on its own.**

Adding MCP tools would never fix runtime performance — that isn't what MCP is
for. Full reasoning: [architecture.md](architecture.md).

---

## TDMCP API facts (read `--schema`, never guess)

- Operator types are **suffixed**: `noiseTOP`, not `noise`.
- `get_help` takes TD **operator types** (`types` / `pattern` / `family` /
  `verbose`), *not* tool names.
- `set_parameters` needs `{path, values: {...}}`; expressions as
  `{"expr": "..."}`.
- TD Python needs **`math.sin`** — bare `sin` → `NameError`, which blanks the
  TOP.
- `inspect_values` wants `sample_grid`.
- **26 tools total.** Not in OpenCode's `search()` index (loaded at startup) —
  list them with `tools/tdmcp_probe.py` and no args.

---

## Corrective habits these findings imply

1. **Read `--schema` before every call.** Three separate bugs this session were
   schema-shaped, not logic-shaped.
2. **A plausible number is not proof.** `Tempo: 120.0` was indistinguishable
   from my own initialised default. Only moving Ableton to 144 proved it.
3. **Trust raw output over my regex on it.** Two "no matches" results were my
   patterns failing on escaped JSON, not the data being absent.
