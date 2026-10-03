# -*- coding: utf-8 -*-
"""What else does this server expose? resources/list and prompts/list."""
import importlib.util
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "tdmcp_probe", os.path.join(HERE, "tdmcp_probe.py"))
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)

p.rpc("initialize", {
    "protocolVersion": "2025-06-18",
    "capabilities": {},
    "clientInfo": {"name": "opencode-probe", "version": "1.0"},
})
p.rpc("notifications/initialized", {}, notify=True)

for method in ("resources/list", "prompts/list", "resources/templates/list"):
    try:
        r = p.rpc(method, {})
        print("=== {0} ===".format(method))
        print(json.dumps(r)[:700])
    except SystemExit as e:
        print("=== {0} -> {1} ===".format(method, e))
