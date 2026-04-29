# ADR-0006: Broker Runtime→Gateway tokens through AgentCore Identity Token Vault

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Security, Platform
- **Tags:** auth, m2m, agentcore-identity

## Context

Given ADR-0005 (Cognito machine client), the agent process running inside
AgentCore Runtime still needs a safe, automatic way to *obtain* a Cognito
access token at tool-call time. Embedding the client secret in the runtime
image, passing it as an environment variable, or having the agent hand-roll
OAuth2 client-credentials requests are all worse than letting AgentCore
Identity do it.

AgentCore provides a managed **Token Vault** plus **OAuth2 Credential
Provider** abstraction. A code decorator (`@requires_access_token`) in the
agent performs a two-stage lookup:

1. `GetOauth2CredentialProvider` — look up provider metadata (ARN, vendor,
   grant type).
2. `GetResourceOauth2Token` — fetch the actual access token.

## Decision

Provision a stack-owned **OAuth2 Credential Provider**
(`${stack_name_base}-runtime-gateway-auth`) that Token Vault manages. The
provider is configured with:

- `DiscoveryUrl` = Cognito user pool OIDC discovery URL.
- `ClientId` / `ClientSecretArn` = the machine client from ADR-0005.

Because CloudFormation does not ship first-party coverage for this resource
today, a small **Custom Resource backed by a dedicated Lambda**
(`oauth2-provider`) creates/updates/deletes it during deploy. The Lambda is
IAM-scoped to:

- `bedrock-agentcore:*Oauth2CredentialProvider` on
  `token-vault/default[/oauth2credentialprovider/*]`,
- `bedrock-agentcore:*TokenVault` on `token-vault/default[/*]`,
- `secretsmanager:*` scoped to
  `bedrock-agentcore-identity!default/oauth2/*` (where Token Vault stores
  its own secrets).

The agent's execution role is granted
`bedrock-agentcore:GetOauth2CredentialProvider` and
`bedrock-agentcore:GetResourceOauth2Token` plus read on both the machine
client secret and the vault's OAuth2 secret.

## Alternatives Considered

- **Agent requests tokens itself using the machine client secret.**
  Rejected: widens the blast radius of the secret and duplicates platform
  capability.
- **Rotate client secrets frequently via Lambda and mount into the
  container.** Rejected: complex, still puts secret material in the
  container, and does not match the AgentCore Identity model.
- **Skip OAuth2 entirely and use SigV4 to the Gateway.** Rejected: the
  Gateway's authorizer is JWT-only (ADR-0005).

## Consequences

### Positive
- Agent code becomes a one-liner (`@requires_access_token`) — no secret
  handling.
- Audit trail: token issuance flows through AgentCore Identity, not custom
  code.
- Easy to rotate: rotate the Cognito client secret and the vault picks it
  up via its secret reference.

### Negative / Trade-offs
- Adds a custom-resource Lambda to the deploy graph and its IAM policy
  surface.
- Requires wildcard-style permissions on `token-vault/default/*` because
  of how the service evaluates vault container + nested-resource
  permissions.
- Bound to AgentCore Identity's availability and semantics.

### Neutral
- `GATEWAY_CREDENTIAL_PROVIDER_NAME` is passed to the runtime as an env
  var so the decorator can look up the right provider without hard-coding.

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts::createAgentCoreGateway` — provisions the
  custom resource, the Lambda provider, and scoped IAM.
- `infra-cdk/lambdas/oauth2-provider/` — Lambda that creates/deletes the
  OAuth2 credential provider.
- `patterns/utils/auth.py` and `tools/gateway.py` — agent-side usage.
- `docs/RUNTIME_GATEWAY_AUTH.md` — end-to-end diagram.

## References

- Internal: `docs/RUNTIME_GATEWAY_AUTH.md`
- External: [Bedrock AgentCore Identity](https://docs.aws.amazon.com/bedrock-agentcore/latest/devguide/identity.html)
