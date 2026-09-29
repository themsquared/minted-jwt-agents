"""A backend that accepts no static API key.

It trusts exactly one thing: a JWT signed by the gateway's private key,
checked against the public key it was given at startup. No shared secret
lives here, so there is nothing on this side worth stealing either.
"""
import json
import os
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import jwt  # PyJWT

PUBLIC_KEY_PATH = os.environ.get("PUBLIC_KEY_PATH", "/keys/signing-key.pub.pem")
EXPECTED_ISS = os.environ.get("EXPECTED_ISS", "agentgateway-demo")
EXPECTED_AUD = os.environ.get("EXPECTED_AUD", "orders-api")

with open(PUBLIC_KEY_PATH) as f:
    PUBLIC_KEY = f.read()

ORDERS = [
    {"id": "ord-1001", "status": "shipped", "total": 42.50},
    {"id": "ord-1002", "status": "pending", "total": 18.00},
]


def log(msg):
    print(msg, file=sys.stderr, flush=True)


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body):
        data = json.dumps(body, indent=2).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, fmt, *args):  # quiet default access log
        pass

    def do_GET(self):
        if self.path == "/healthz":
            return self._send(200, {"ok": True})
        if self.path != "/orders":
            return self._send(404, {"error": "not found"})

        auth = self.headers.get("authorization", "")
        if not auth.startswith("Bearer "):
            log("REJECT no bearer token")
            return self._send(401, {"error": "missing bearer token"})
        token = auth[len("Bearer "):]
        # Deliberately log the raw token. Tokens end up in logs in real
        # systems too; the demo shows why that stops mattering once they expire.
        log(f"TOKEN {token}")

        try:
            header = jwt.get_unverified_header(token)
            claims = jwt.decode(
                token,
                PUBLIC_KEY,
                algorithms=["ES256"],
                audience=EXPECTED_AUD,
                issuer=EXPECTED_ISS,
                options={"require": ["exp", "iat", "iss", "aud", "sub"]},
            )
        except jwt.ExpiredSignatureError:
            log("REJECT expired token")
            return self._send(401, {"error": "token expired"})
        except jwt.InvalidTokenError as e:
            log(f"REJECT invalid token: {e}")
            return self._send(401, {"error": f"invalid token: {e}"})

        if "orders:read" not in str(claims.get("scope", "")).split():
            return self._send(403, {"error": "scope orders:read required"})

        now = int(time.time())
        log(f"ACCEPT sub={claims['sub']} exp_in={claims['exp'] - now}s")
        return self._send(200, {
            "orders": ORDERS,
            "authenticated_as": claims["sub"],
            "token_header": header,
            "token_claims": claims,
            "token_expires_in_seconds": claims["exp"] - now,
        })


if __name__ == "__main__":
    log(f"backend listening on :8080, trusting public key {PUBLIC_KEY_PATH}")
    ThreadingHTTPServer(("0.0.0.0", 8080), Handler).serve_forever()
