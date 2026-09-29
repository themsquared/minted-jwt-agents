#!/usr/bin/env bash
# End-to-end walkthrough. Run after: ./keygen.sh && docker compose up -d --build
set -euo pipefail
cd "$(dirname "$0")"
step() { printf '\n\033[1m== %s\033[0m\n' "$*"; }

step "1. The agent holds no key: its environment"
docker compose exec -T agent env | sort

step "1b. ...and no PEM anywhere in its filesystem"
if docker compose exec -T agent sh -c 'grep -rl "PRIVATE KEY" / --exclude-dir=proc --exclude-dir=sys --exclude-dir=usr 2>/dev/null'; then
  echo "FOUND a private key in the agent container"; exit 1
else
  echo "no private key found in the agent container"
fi

step "2. The agent calls the backend through agentgateway"
docker compose exec -T agent python /agent/agent.py

step "3. A second call gets a different token (fresh iat/exp)"
sleep 1
docker compose exec -T agent python /agent/agent.py | grep -E '"(iat|exp)"'

step "4. Calling the backend directly with no token"
docker compose exec -T attacker python /attacker/replay.py

step "5. Lift the most recent token out of the backend's logs"
TOKEN=$(docker compose logs --no-log-prefix backend | awk '/^TOKEN /{t=$2} END{print t}')
echo "${TOKEN:0:60}..."

step "6. Replay it immediately (inside its lifetime)"
docker compose exec -T attacker python /attacker/replay.py "$TOKEN"

step "7. Wait out the 15s ttl, then replay the same token"
sleep 16
docker compose exec -T attacker python /attacker/replay.py "$TOKEN"

step "8. The caveat: anything that can reach the gateway gets a minted token"
docker compose exec -T attacker python /attacker/via_gateway.py
echo "(the inbound leg needs its own authentication: see the README)"
