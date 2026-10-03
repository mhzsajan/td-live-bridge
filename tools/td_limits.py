# -*- coding: utf-8 -*-
"""Two probes that decide whether TDMCP constrains an agent:

1. initialize capabilities  - can the server push notifications, or is it
   strictly request/response (i.e. I must always poll)?
2. burst of N cheap calls   - does the Tune page rate limiter throttle me?
"""
import importlib.util
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "tdmcp_probe", os.path.join(HERE, "tdmcp_probe.py"))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

init = p.rpc("initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "opencode-probe", "version": "1.0"},
})
print("=== SERVER CAPABILITIES ===")
print(json.dumps(init.get("result", {}).get("capabilities", {}), indent=2))
print("instructions present:", bool(init.get("result", {}).get("instructions")))
p.rpc("notifications/initialized", {}, notify=True)

print("=== BURST: 12 rapid get_errors calls ===")
lat = []
errors = 0
for i in range(12):
    t0 = time.time()
    r = p.rpc("tools/call", {"name": "get_errors", "arguments": {}})
    lat.append((time.time() - t0) * 1000)
    txt = json.dumps(r)
    if r.get("result", {}).get("isError") or "rate" in txt.lower() or "cooldown" in txt.lower():
        errors += 1
        print("  call {0}: THROTTLED/ERROR -> {1}".format(i + 1, txt[:220]))
print("latencies ms: " + ", ".join("{0:.0f}".format(x) for x in lat))
print("min {0:.0f}  max {1:.0f}  avg {2:.0f}".format(
    min(lat), max(lat), sum(lat) / len(lat)))
print("throttled/error calls: {0}/{1}".format(errors, len(lat)))
