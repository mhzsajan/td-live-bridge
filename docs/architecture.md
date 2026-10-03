# Architecture — build time vs run time

The single decision that shaped this project, and the number that forced it.

---

## The number

```
MCP round trip     17 – 33 ms
60 fps frame budget     16.7 ms
```

**One MCP call costs more than a whole frame** — before any rendering happens.
Add that a language model's turn takes seconds, and the conclusion is
inescapable:

> Visuals cannot be driven through MCP.

Not because TDMCP's tools are weak — because of the arithmetic.

---

## The split

```
┌────────────────────────────┐      ┌─────────────────────────────────┐
│  BUILD TIME  (MCP)         │      │  RUN TIME  (TD-internal)        │
│                            │      │                                 │
│  create operators          │      │  frame-start pump (executeDAT)  │
│  wire them up              │ ───► │  persistent socket to :9877     │
│  set parameters            │ once │  expressions → pars → channels  │
│  read errors               │      │  Link CHOP for tempo/phase      │
│  screenshots               │      │  CHOP chains for visuals        │
│                            │      │                                 │
│  OpenCode authors here     │      │  cooks at 60 fps, no MCP        │
└────────────────────────────┘      └─────────────────────────────────┘
```

**MCP is for authoring networks. The network then runs on its own.**

This is why Step 1 built a *runtime* component — a frame-driven pump inside
TD — rather than a tool OpenCode calls. OpenCode builds it once; TD executes
it forever.

---

## What this ruled out

### ❌ Building a competing TD MCP

`execute_code` gives arbitrary Python with filesystem access (proven: it wrote
into this machine's temp dir). That is the **same ceiling** a bespoke server
would have.

We would reimplement working tools to reach an identical endpoint, then inherit
the maintenance. TDMCP's Shared Use License permits modifying it for your own
projects but prohibits redistributing it as a product — so a fork couldn't be
shared anyway.

**Verdict: don't.**

### ❌ Server-push / subscriptions

`resources.subscribe: false` — the server can never notify me. Every read is a
poll I initiate.

But this matters far less than it first appears: **at 60 fps, polling from
OpenCode was never the plan.** The polling happens *inside TD*, in a
frame-start callback, where it costs 0.033 ms. MCP notifications would have
been the wrong tool for the job.

### ❌ TDAbleton / Max for Live

No Max on this PC. UDP 9882 is inbound fire-and-forget with no replies, so
reads must go over TCP 9877 anyway.

---

## What this ruled *in*

A thin **domain layer** nobody ships:

```
TCP 9877  →  poller  →  dependable property  →  expression par  →  CHOP channel
            (frame-    (TDF.createProperty)    (me.LiveTempo)     (Tempo)
             start)
```

Each hop has a reason:

| Hop | Why |
|---|---|
| `executeDAT` frame-start | Main thread. TD is not thread-safe, so no background thread. |
| Non-blocking `select(0)` | Never stalls the frame — the skill warns execute DATs run on the main thread. |
| `TDF.createProperty(dependable=True)` | A plain `self.x = …` does **not** trigger downstream recooks. |
| Expression par | Skill's *State Output Pattern*: downstream references pars, never extension properties directly. Visible in UI, linkable, fetchable. |
| `parameterCHOP` | Turns pars into channels other operators can consume. |

### Supplement, don't replace

If generic tools later feel clumsy for show work, add thin `td_*` domain tools
**alongside** TDMCP. That's a call to make from real friction — not before it.

---

## Future: TD → Live (the missing arrow)

UDP 9882, inbound only, no replies — good for fire-and-forget writes: trigger
clips, change tempo from visuals.

Because there's no acknowledgement channel, design it as **one-way intent**:
TD assumes the write landed. Don't build a request/response protocol on a
socket that can't answer.
