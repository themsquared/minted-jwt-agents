#!/usr/bin/env bash
# Generate the gateway's ES256 signing key pair.
# The private half is mounted ONLY into agentgateway.
# The public half is mounted ONLY into the backend.
# The agent container gets neither.
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p keys/private keys/public
if [[ -f keys/private/signing-key.pem ]]; then
  echo "keys/private/signing-key.pem already exists, leaving it alone"
else
  openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out keys/private/signing-key.pem 2>/dev/null
  chmod 644 keys/private/signing-key.pem   # readable by the gateway container user
fi
openssl pkey -in keys/private/signing-key.pem -pubout -out keys/public/signing-key.pub.pem 2>/dev/null
echo "private key -> keys/private/signing-key.pem (gateway only)"
echo "public key  -> keys/public/signing-key.pub.pem (backend only)"
