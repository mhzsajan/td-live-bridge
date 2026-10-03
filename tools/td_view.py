# -*- coding: utf-8 -*-
"""Capture a TouchDesigner operator's output to a PNG on disk.

view_operator returns the image inline as base64; this writes it out so it
can be previewed like any other image.

Usage: python td_view.py /project1/proof_out out.png [resolution]
"""
import base64
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "tdmcp_probe", os.path.join(HERE, "tdmcp_probe.py"))
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)

src = sys.argv[1]
dst = sys.argv[2]
resolution = sys.argv[3] if len(sys.argv) > 3 else "low"

probe.rpc("initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "opencode-probe", "version": "1.0"},
})
probe.rpc("notifications/initialized", {}, notify=True)

result = probe.rpc("tools/call", {
    "name": "view_operator",
    "arguments": {"path": src, "resolution": resolution},
})

if result.get("result", {}).get("isError"):
    print("ERROR:", json.dumps(result)[:800])
    raise SystemExit(1)

payload = json.loads(result["result"]["content"][0]["text"])

# The component writes the PNG to its Image Cache Path and returns the
# location, unless Inline Images is on, in which case it returns base64.
if "file" in payload:
    src_file = payload["file"]
    if not os.path.exists(src_file):
        print("server reported a file that is missing:", src_file)
        raise SystemExit(1)
    with open(src_file, "rb") as fh:
        blob = fh.read()
else:
    data = payload.get("data") or payload.get("image") or payload.get("base64")
    if not data:
        print("keys returned:", list(payload))
        print(json.dumps(payload)[:600])
        raise SystemExit(1)
    blob = base64.b64decode(data)

with open(dst, "wb") as fh:
    fh.write(blob)
print("wrote {0} ({1} bytes) from {2}".format(
    dst, len(blob), payload.get("file", "inline base64")))
