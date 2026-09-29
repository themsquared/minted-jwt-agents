"""The agent. It knows where the gateway is and nothing else.

No API key, no private key, no token. It asks the gateway for orders and
the gateway signs a fresh JWT for the backend on this request.
"""
import json
import os
import urllib.request

GATEWAY = os.environ.get("GATEWAY_URL", "http://agentgateway:3000")

with urllib.request.urlopen(f"{GATEWAY}/orders", timeout=5) as resp:
    body = json.load(resp)

print(json.dumps(body, indent=2))
