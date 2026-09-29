"""The caveat: the gateway mints for anyone who can reach its listener.

This demo leaves the inbound leg (caller -> gateway) unauthenticated on
purpose, to keep the backend leg readable. Here is what that costs.
"""
import json
import urllib.request

with urllib.request.urlopen("http://agentgateway:3000/orders", timeout=5) as resp:
    body = json.load(resp)
print(resp.status, "authenticated_as:", body["authenticated_as"])
