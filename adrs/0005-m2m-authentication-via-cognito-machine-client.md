# ADR-0005: Machine-to-machine auth via a dedicated Cognito machine client

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Security, Platform
- **Tags:** auth, m2m, security

## Context

The AgentCore Gateway is itself a protected resource: agents running inside
AgentCore Runtime must authenticate to invoke tools, but this authentication
is *service-to-service* and must not depend on an individual user's session.
We need a token that the Runtime can obtain headlessly and that the Gateway
can validate against the same Cognito trust anchor used for user JWTs.

Mixing user-facing and machine-facing authentication on a single client is
unsafe (different flows, different secret-handling expectations, different
scope semantics).

## Decision

Provision a separate **Cognito Machine Client** and **Resource Server** in
the same User Pool:

- **Resource Server** `${stack_name_base}-gateway` with `read` and `write`
  scopes — defines the API surface the Gateway accepts tokens for.
- **Machine Client** with `generateSecret: true` and the OAuth2
  **Client Credentials** flow enabled, scoped to the Resource Server scopes.
- The machine client secret is mirrored into **AWS Secrets Manager**
  (`/${stack_name_base}/machine_client_secret`) so test scripts and the
  OAuth2 credential-provider Lambda can read it without unsafe CDK
  resolution at runtime.

The AgentCore Gateway's authorizer is configured as `CUSTOM_JWT` with
`allowedClients: [machineClient.userPoolClientId]` and the Cognito
discovery URL, so only tokens minted for the machine client are accepted.

## Alternatives Considered

- **Reuse the user-facing client for service calls.** Rejected: mixing
  public and confidential client semantics is a security anti-pattern.
- **IAM SigV4 between Runtime and Gateway.** Rejected: AgentCore Gateway's
  authorizer model expects OAuth2 JWTs; forcing IAM would fight the
  platform.
- **Static API key.** Rejected: rotation and revocation are manual; no
  audience/scope enforcement.

## Consequences

### Positive
- Clean separation between "user identity" and "service identity".
- Gateway validates scoped JWTs natively via Cognito's discovery URL.
- Secret is centralized in Secrets Manager with IAM-scoped access.

### Negative / Trade-offs
- Two clients to manage in the same pool; naming/documentation must make
  the distinction obvious.
- The machine-client secret is a high-value credential — mis-scoping IAM
  on the secret is a real risk.

### Neutral
- Scopes (`read`, `write`) are intentionally coarse today. Refine as
  tool-level authorization needs emerge.

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts` —
  - `createMachineAuthentication` (~line 860) creates the Resource Server,
    Machine Client, and Secrets Manager mirror.
  - `createAgentCoreGateway` wires `authorizerType: "CUSTOM_JWT"` with the
    machine client as the only allowed client.
- `docs/RUNTIME_GATEWAY_AUTH.md` — end-to-end M2M auth walk-through.

## References

- Internal: `docs/RUNTIME_GATEWAY_AUTH.md`
- External: [OAuth2 Client Credentials Grant (RFC 6749 §4.4)](https://datatracker.ietf.org/doc/html/rfc6749#section-4.4)
