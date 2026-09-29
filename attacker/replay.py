"""Replay a token lifted from the backend's logs, straight at the backend.

Usage: python replay.py <token>     (or with no token, to try an unauthenticated call)
"""
import json
import sys
import urllib.error
import urllib.request

req = urllib.request.Request("http://backend:8080/orders")
if len(sys.argv) > 1:
    req.add_header("Authorization", f"Bearer {sys.argv[1]}")
try:
    with urllib.request.urlopen(req, timeout=5) as resp:
        body = json.load(resp)
        print(resp.status, "authenticated_as:", body["authenticated_as"],
              "expires_in:", body["token_expires_in_seconds"], "s")
except urllib.error.HTTPError as e:
    print(e.code, json.load(e)["error"])
