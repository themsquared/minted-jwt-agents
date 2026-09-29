# minted-jwt-agents

An AI agent calls a backend through [agentgateway](https://agentgateway.dev) and holds no credential for it. No API key in the environment, no key file on disk, no token. agentgateway signs a fresh ES256 JWT with its own private key on every request (`backendAuth.jwtSign`, new in agentgateway v1.5), and the backend verifies it with the matching public key. Tokens live 15 seconds, so one lifted from a log is worthless shortly after it was minted.

This is the same key-pair JWT pattern the Snowflake SQL API requires, run locally against a mock backend with `docker compose`. No cloud account needed.

## The problem

A static API key for a backend is a standing credential. It does not expire, it is valid from anywhere, and whoever copies it out of an agent's environment (a compromised dependency, a leaked `.env`, a prompt-injected tool call that runs `env`) can use it until someone notices and rotates it.

Moving the key to a gateway already takes it out of the agent's process. Signing a short-lived token per request goes one step further: there is no long-lived bearer secret on the gateway-to-backend connection at all. The private key never leaves the gateway, and what crosses the wire expires in seconds.

## What the demo proves

1. The agent container's environment and filesystem hold no key.
2. The agent's call through agentgateway succeeds, and the backend reports the claims and expiry of the token it received.
3. Each request gets a freshly signed token.
4. Calling the backend directly with no token fails with 401.
5. A token lifted from the backend's logs replays fine inside its lifetime, and fails with `401 token expired` once the 15s `ttl` passes.
6. The caveat, shown on purpose: anything that can reach the gateway's listener gets a minted token. The inbound leg needs its own authentication.

## Quickstart

Requirements: Docker with Compose v2, `openssl`. Tested on macOS (Docker Desktop, Apple silicon) with agentgateway v1.5.0.

```bash
git clone https://github.com/themsquared/minted-jwt-agents.git
cd minted-jwt-agents
./keygen.sh
docker compose up -d --build
./demo.sh
```

Tear down:

```bash
docker compose down
```

Check the gateway config against the v1.5.0 schema without starting anything:

```bash
docker run --rm -v "$PWD/gateway/config.yaml:/config/config.yaml:ro" -v "$PWD/keys/private:/keys:ro" \
  cr.agentgateway.dev/agentgateway:v1.5.0 -f /config/config.yaml --validate-only
```

## The gateway config

```yaml
gateways:
  default:
    port: 3000
routes:
- name: orders-api
  backends:
  - host: backend:8080
    policies:
      backendAuth:
        jwtSign:
          signingKey:
            file: /keys/signing-key.pem
          alg: ES256
          kid: agw-demo-key-1
          claims:
            iss: agentgateway-demo
            sub: orders-agent
            aud: orders-api
            scope: orders:read
          ttl: 15s
```

Every field is from the v1.5.0 [config schema](https://github.com/agentgateway/agentgateway/blob/v1.5.0/schema/config.md) and the [Signed JWT (jwtSign)](https://agentgateway.dev/docs/standalone/latest/documentation/configuration/security/backend-authn/jwt-sign/) docs page. `iat` and `exp` are set by the signer and cannot be configured under `claims`. `iat` is backdated 10 seconds for clock skew, so a decoded token spans `ttl + 10s`.

## Architecture

```
agent (no key)          agentgateway (private key)         backend (public key)
     |                          |                                 |
     |-- GET /orders ---------->|                                 |
     |                          |-- sign ES256 JWT, exp = now+15s |
     |                          |-- Authorization: Bearer <jwt> ->|
     |                          |                                 |-- verify sig, iss, aud, exp, scope
     |<------------------------ 200 ------------------------------|
```

| Container | Holds | Mount |
|---|---|---|
| `agentgateway` | ES256 private key | `keys/private` |
| `backend` | public key only | `keys/public` |
| `agent` | nothing but its code | `agent/` |
| `attacker` | nothing; plays whoever can read the backend's logs | `attacker/` |

The backend logs every raw token it receives on purpose. Tokens end up in logs in real systems too; `demo.sh` lifts one from there to replay it.

## Notes and limits

- **Claims are static per route.** The `sub` the backend sees is the one you configured, not the calling agent's identity. One route (or backend) per agent identity is the way to get distinct subjects.
- **There is no `jti`.** Two requests signed in the same second carry identical claims. ECDSA signatures are randomized, so the token bytes still differ, but the backend cannot tell a replay from a fresh request inside the lifetime. Keep `ttl` short.
- **Key rotation.** The native binary watches the key file and reloads on change. On Docker Desktop, replacing the bind-mounted key file did not trigger a reload in my testing; restart the gateway container after rotating. Publish the new public key to the backend before you rotate the private key, or requests fail with `Signature verification failed` until both sides match.
- **The inbound leg is open in this demo.** Put agentgateway's JWT authentication or workload identity in front of the listener for anything real.
- `keygen.sh` makes the private key `644` so the gateway container can read it through the bind mount. That is a demo convenience. Linux hosts were not tested.

## Topics

`agentgateway` `ai-agents` `jwt` `ai-gateway` `workload-identity` `zero-trust` `docker-compose`

## License

Apache-2.0
