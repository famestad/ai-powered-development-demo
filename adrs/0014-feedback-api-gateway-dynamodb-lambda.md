# ADR-0014: Feedback API on API Gateway + Lambda + DynamoDB

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Platform, Frontend
- **Tags:** api, storage, application-data

## Context

Outside of agent invocations, the app needs a place to persist
application data that the frontend writes directly — starting with
thumbs-up/down feedback on agent responses. This must:

- Authenticate the same Cognito user that invoked the agent.
- Validate request bodies server-side.
- Be reviewable, auditable, and cheap at low QPS.
- Serve as the **template** for future lightweight REST endpoints
  (e.g. saved searches, reporting).

## Decision

Provision a single **REST API Gateway** with a **Cognito User Pools
Authorizer** fronting a Python Lambda (`PythonFunction`,
`ARM_64`, PowerTools layer) that writes to a **DynamoDB** table:

- **Auth:** `CognitoUserPoolsAuthorizer` on the same pool used for
  the frontend.
- **Validation:** API Gateway `RequestValidator` with body and
  parameter validation.
- **CORS:** preflight allowed for the Amplify URL and
  `http://localhost:3000`; runtime Lambda re-checks origin via
  `CORS_ALLOWED_ORIGINS` env var.
- **Throttling:** 100 rps steady, 200 burst.
- **Caching:** 5-minute TTL, encrypted cache cluster (`0.5` size).
- **Observability:** access logs in CloudWatch (JSON std fields),
  method-level logging at `INFO`, data tracing on, X-Ray tracing on.
- **DynamoDB:**
  - `PAY_PER_REQUEST` billing.
  - `feedbackId` partition key.
  - GSI `feedbackType-timestamp-index` for queries over time.
  - AWS-managed encryption, PITR enabled.
  - `RemovalPolicy.DESTROY` for demo purposes (revisit for prod).

The API URL is exported as the `FeedbackApiUrl` stack output and also
written to SSM so the frontend can discover it.

## Alternatives Considered

- **AppSync GraphQL.** Rejected: overkill for a single endpoint and
  adds a different auth model to reason about.
- **Write directly from the frontend to DynamoDB with Cognito
  Identity Pool credentials.** Rejected: broader IAM surface on the
  client than necessary; harder to add server-side validation or
  rate limiting.
- **Lambda Function URL.** Rejected: loses API Gateway's native
  Cognito authorizer, request validation, WAF attach point, and
  access logs.

## Consequences

### Positive
- Template is reusable for future endpoints — copy the method +
  model.
- Server-side validation, throttling, caching, and tracing ship out
  of the box.
- DynamoDB + PITR gives a cheap, highly available store with a real
  recovery story.

### Negative / Trade-offs
- CORS has a known TODO: backend deploys before frontend, so
  preflight uses a broader allow-list than ideal (called out in
  `backend-stack.ts` comments and in the Lambda source).
- `RemovalPolicy.DESTROY` is fine for demos but must change for
  production.
- Cache cluster adds a small fixed cost.

### Neutral
- The PowerTools layer pin includes a specific version (`:18`);
  revisit periodically.

## Implementation Notes

- `infra-cdk/lib/backend-stack.ts::createFeedbackTable` (~line 443)
  and `createFeedbackApi` (~line 498).
- `infra-cdk/lambdas/feedback/index.py` — handler.
- `frontend/src/services/feedbackService.ts` — client.

## References

- Internal: this ADR is the canonical description of the pattern for
  future REST endpoints.
- External: [API Gateway best practices](https://docs.aws.amazon.com/apigateway/latest/developerguide/security-best-practices.html),
  [DynamoDB PITR](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/PointInTimeRecovery.html)
