# -*- coding: utf-8 -*-
"""Raw MCP-over-HTTP probe for the TDMCP component running inside TouchDesigner.

Speaks streamable-HTTP MCP directly, so it can verify the server before
opencode is restarted (opencode only reads MCP config at startup).

Usage:
  python tdmcp_probe.py            # initialize -> tools/list
  python tdmcp_probe.py <tool> '<json arguments>'   # then tools/call
"""
import json
import sys
import urllib.request
import urllib.error

URL = "http://127.0.0.1:13316/mcp"
HEADERS = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
}
_session = None


def _parse(body, content_type):
    """Servers reply either as plain JSON or as SSE (data: lines)."""
    if "text/event-stream" in (content_type or ""):
        payloads = []
        for line in body.splitlines():
            if line.startswith("data:"):
                chunk = line[5:].strip()
                if chunk and chunk != "[DONE]":
                    payloads.append(json.loads(chunk))
        return payloads[-1] if payloads else None
    if not body.strip():
        return None
    return json.loads(body)


def rpc(method, params=None, notify=False):
    global _session
    payload = {"jsonrpc": "2.0", "method": method}
    if not notify:
        payload["id"] = 1
    if params is not None:
        payload["params"] = params
    headers = dict(HEADERS)
    if _session:
        headers["Mcp-Session-Id"] = _session
    req = urllib.request.Request(
        URL, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            sid = resp.headers.get("Mcp-Session-Id")
            if sid:
                _session = sid
            return _parse(resp.read().decode("utf-8", "replace"),
                          resp.headers.get("Content-Type"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:400]
        raise SystemExit("HTTP {0} from {1}: {2}".format(e.code, method, detail))


def main():
    init = rpc("initialize", {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "opencode-probe", "version": "1.0"},
    })
    info = init.get("result", {}).get("serverInfo", {})
    print("connected: {0} {1} (protocol {2})".format(
        info.get("name"), info.get("version"),
        init.get("result", {}).get("protocolVersion")))
    if _session:
        print("session id:", _session)
    rpc("notifications/initialized", {}, notify=True)

    if len(sys.argv) >= 2 and sys.argv[1] != "--schema":
        tool = sys.argv[1]
        raw = sys.argv[2] if len(sys.argv) > 2 else "{}"
        # PowerShell mangles embedded quotes on the command line, so an
        # argument starting with '@' names a file holding the JSON instead.
        if raw.startswith("@"):
            with open(raw[1:], "r", encoding="utf-8") as fh:
                raw = fh.read()
        result = rpc("tools/call", {"name": tool, "arguments": json.loads(raw)})
        # Full text: truncating hides `count` and the tail of long responses.
        # A separate --limit arg can still cap it when needed.
        cap = int(sys.argv[3]) if len(sys.argv) > 3 else 200000
        print(json.dumps(result, indent=2)[:cap])
        return

    listing = rpc("tools/list", {})
    tools = listing.get("result", {}).get("tools", [])
    if len(sys.argv) >= 2 and sys.argv[1] == "--schema":
        # Dump the exact input schema so arguments are never guessed.
        wanted = sys.argv[2] if len(sys.argv) > 2 else None
        for t in tools:
            if wanted and t.get("name") != wanted:
                continue
            print("### {0}".format(t.get("name")))
            print(t.get("description", "").strip()[:400])
            print(json.dumps(t.get("inputSchema", {}), indent=2))
        return
    print("tools: {0}".format(len(tools)))
    for t in tools:
        print("  - {0}".format(t.get("name")))


if __name__ == "__main__":
    main()
