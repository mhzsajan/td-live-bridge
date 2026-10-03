# AbleBridgePlus wire protocol — TCP 9877

Verified empirically against a live session. **20 sequential calls on one
socket succeeded**, proving persistence works.

---

## Framing

```
→  {"type": "<command>", "params": {…}}\n      UTF-8, newline-terminated
←  {"status": "success", "result": {…}}\n       one JSON object per line
```

Both directions are **newline-delimited JSON**. Accumulate `recv()` bytes and
split on `\n` *before* decoding.

Reference implementations:

- Server: `AbleBridgePlus/AbleBridgePlus/__init__.py` (`_handle_client`, ~line 877)
- Client: `AbleBridgePlus/MCP_Server/connections/ableton.py` (`_recv_until`, ~line 126)

### Error shape

```
←  {"status": "error", …}\n
```

The server also writes a JSON error response on malformed input rather than
closing the connection.

---

## The three commands this bridge uses

`watch_session` is a **composed MCP tool**, not a wire command. It is assembled
in `MCP_Server/tools/doctor.py` (lines 278–295) from three separate round
trips. A poller must issue them itself:

| # | Command | Returns |
|---|---|---|
| 1 | `get_song_transport` | `current_time`, `is_playing`, `tempo`, `signature_numerator/denominator`, `loop_*`, `song_length`, `record_mode`, `punch_in/out`, `count_in_duration`, `is_counting_in` |
| 2 | `get_playing_clips` | `{"playing_clips": […], "count": N}` |
| 3 | `get_track_meters` | see caveat below |

```python
payload = json.dumps({"type": cmd, "params": {}}) + "\n"
sock.sendall(payload.encode("utf-8"))
line = read_until_newline(sock)
msg = json.loads(line)
if msg["status"] != "success":
    raise RuntimeError(msg.get("error") or msg.get("message") or msg)
result = msg["result"]
```

---

## Verified response examples

### `get_song_transport`

```json
{"status": "success", "result": {
  "current_time": 0.0, "is_playing": false, "tempo": 120.0,
  "signature_numerator": 4, "signature_denominator": 4,
  "loop_enabled": false, "loop_start": 18456.0, "loop_length": 192.0,
  "song_length": 19852.0, "record_mode": false,
  "punch_in": false, "punch_out": false,
  "count_in_duration": 0, "is_counting_in": false
}}
```

### `get_playing_clips`

```json
{"status": "success", "result": {"playing_clips": [], "count": 0}}
```

### `get_track_meters`

```json
{"status": "success", "result": {
  "index": 0, "name": "VIDEO",
  "output_meter_left": 0.0, "output_meter_right": 0.0,
  "playing_slot_index": -1, "fired_slot_index": -1
}}
```

---

## ⚠️ Unverified: multi-track meter shape

The session tested had **one track**, and `get_track_meters` returned a
**single flat dict** — not a list.

The MCP server's own code hints at both shapes:

```python
# doctor.py:294
"meters": meters.get("tracks", meters) if isinstance(meters, dict) else meters
```

So it *expects* `{"tracks": [...]}` might exist. With one track it did not.

**Before designing multi-track channels, query a set with 2+ tracks and confirm
which shape arrives.** Do not build channel naming against an assumption.

---

## Connection rules

- **TCP 9877 is threaded per client** — TD polling and the MCP server coexist.
- **Hold the socket open.** Each *new* connection fires a `Client connected`
  message in Live's status bar; reconnect-per-poll spams it.
- Loopback refuses fast when Live is closed, so a guarded connect attempt is
  cheap — but only attempt it when not already connected.

---

## The other ports (not used here)

| Port | Protocol | Notes |
|---|---|---|
| 9882 | UDP, JSON | **Inbound only, no replies.** TD → Live writes only. |
| 9878 / 9879 | OSC | M4L bridge — unused (no Max on this PC) |
| 9880 | HTTP | web dashboard — unused |

Because UDP 9882 cannot acknowledge, any TD → Live write must be designed as
**one-way intent**: assume it landed.
