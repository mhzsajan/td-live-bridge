# -*- coding: utf-8 -*-
"""Speak the raw AbleBridgePlus TCP protocol directly, the way the TD
extension will. Confirms exact command names, framing, and response shape
before any TouchDesigner code is written.

Wire contract (from MCP_Server/connections/ableton.py):
  out:  json.dumps({"type": ..., "params": ...}) + "\n"   utf-8
  back: one JSON object terminated by "\n"
"""
import json
import socket
import sys

HOST, PORT = "127.0.0.1", 9877


def call(sock, command_type, params=None, timeout=10.0):
    sock.settimeout(timeout)
    payload = (json.dumps({"type": command_type, "params": params or {}}) + "\n")
    sock.sendall(payload.encode("utf-8"))
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(8192)
        if not chunk:
            raise ConnectionError("Ableton closed the connection")
        buf += chunk
    line, _ = buf.split(b"\n", 1)
    return json.loads(line.decode("utf-8", "replace"))


def main():
    sock = socket.create_connection((HOST, PORT), timeout=5)
    print("connected to {0}:{1}".format(HOST, PORT))
    try:
        for cmd in ("get_song_transport", "get_playing_clips", "get_track_meters"):
            try:
                resp = call(sock, cmd)
            except Exception as e:
                print("  {0}: FAILED {1}".format(cmd, e))
                continue
            keys = list(resp)[:8] if isinstance(resp, dict) else type(resp).__name__
            print("  {0}: status={1} keys={2}".format(
                cmd, resp.get("status") if isinstance(resp, dict) else "?", keys))
            print("     " + json.dumps(resp)[:300])
        # does the connection stay usable across many calls? (persistence test)
        n = 0
        for _ in range(20):
            call(sock, "get_song_transport")
            n += 1
        print("20 sequential calls on ONE socket: OK ({0})".format(n))
    finally:
        sock.close()


if __name__ == "__main__":
    main()
