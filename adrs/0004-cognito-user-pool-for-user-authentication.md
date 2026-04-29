# ADR-0004: Use Amazon Cognito User Pool for end-user authentication

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Security, Platform
- **Tags:** auth, security

## Context

The Maplewood agent must authenticate citizens before allowing agent
invocations. We need a managed identity provider that:

- Issues JWTs that both API Gateway (for the Feedback API) and AgentCore
  Runtime (JWT authorizer) can validate natively.
- Supports a standards-based OAuth2 flow for the SPA (Authorization Code
  with PKCE).
- Supports a separate machine-to-machine flow (see ADR-0005).
- Integrates with existing AWS IAM / CloudWatch without extra connectors.

## Decision

Use a single **Cognito User Pool** with:

- **User-facing client:** public SPA client, Authorization Code grant with
  `openid email profile` scopes, password policy enforced, account recovery
  by email only, self sign-up disabled (admins provision users).
- **Managed Login v2** with a Cognito-owned managed-login branding resource
  so the hosted UI works out of the box.
- **Optional admin user** provisioned automatically when `admin_user_email`
  is set in `config.yaml` (Cognito emails temporary credentials).
- **Callback URLs** seeded with the predictable Amplify URL plus localhost
  for local dev (`http://localhost:3000`).

## Alternatives Considered

- **Auth0 / Okta / Entra ID.** Rejected for this baseline: external IdP
  dependency, extra cost, and no native IAM trust. A later ADR can layer an
  external IdP as a Cognito federated provider if Maplewood mandates SSO.
- **Build our own JWT issuer.** Rejected: we do not want to own auth.
- **Amplify Auth (Gen 2).** Rejected to keep IaC centralized in CDK
  (ADR-0002).

## Consequences

### Positive
- Native JWT validation in API Gateway (`CognitoUserPoolsAuthorizer`) and
  AgentCore Runtime (`RuntimeAuthorizerConfiguration.usingJWT`).
- Cognito domain/hosted UI eliminates bespoke login screens.
- Same pool hosts both user flow (ADR-0004) and M2M flow (ADR-0005).

### Negative / Trade-offs
- Cognito has well-known rough edges (limited branding before v2 managed
  login, per-region resources, hard-to-reverse password policy changes).
- User migration off Cognito is non-trivial.
- Self sign-up disabled means we need an admin workflow to onboard users.

### Neutral
- Symbols in password policy are required; enforce at the app UI too to
  give clear validation feedback.

## Implementation Notes

- `infra-cdk/lib/cognito-stack.ts` — `UserPool`, `UserPoolClient`,
  `UserPoolDomain` (v2 managed login), managed login branding, optional
  admin user.
- `infra-cdk/lib/backend-stack.ts` — imports the pool, wires JWT
  authorizer into AgentCore Runtime (line ~228) and API Gateway
  (`CognitoUserPoolsAuthorizer`, line ~582).
- SSM parameters under `/${stack_name_base}/cognito-*` expose pool/client
  IDs for frontend bootstrap and test scripts.

## References

- Internal: `docs/DEPLOYMENT.md`
- External: [Cognito User Pools](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-identity-pools.html),
  [Managed Login v2](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-managed-login.html)
