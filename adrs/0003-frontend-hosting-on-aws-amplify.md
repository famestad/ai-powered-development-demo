# ADR-0003: Host the React frontend on AWS Amplify Hosting

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Platform / Infra, Frontend
- **Tags:** frontend, hosting

## Context

The citizen-facing UI is a React + TypeScript + Vite single-page application
with Tailwind and shadcn components. We need managed, HTTPS-terminated
hosting with a stable URL that Cognito and AgentCore can trust as the
redirect / callback origin. Deployments should be scriptable so that AI
coding assistants and CI can publish the frontend without bespoke infra.

A particular constraint is that Cognito callback URLs and (formerly) CORS
allow-lists must be registered at infrastructure-creation time — so the
frontend URL must be *predictable* before the backend is deployed.

## Decision

Deploy the frontend using **AWS Amplify Hosting**, provisioned by CDK in a
dedicated nested stack (`AmplifyHostingStack`). The predictable URL format
`https://main.{appId}.amplifyapp.com` is computed at synth time and passed to
the Cognito and Backend stacks so callback URLs and CORS origins can be
registered in a single `cdk deploy`. Deployment artifacts are uploaded to a
versioned, SSL-enforced S3 staging bucket.

## Alternatives Considered

- **S3 + CloudFront** static hosting. Rejected: more moving parts (OAC,
  invalidations, cert management) for no meaningful win in this scope.
- **Amplify Gen 2 (fullstack).** Rejected: FAST uses CDK for the bulk of
  infra; pulling Amplify Gen 2 in just for hosting complicates the story.
- **Bring-your-own web server (EC2/ECS).** Rejected: operational overhead not
  justified by a static SPA.

## Consequences

### Positive
- Stable, predictable subdomain before first deploy — unblocks
  callback/CORS registration in the same synth.
- Built-in HTTPS, automatic branch-based deploys (`main` = production).
- Amplify Console gives non-developers visibility into deploy state.

### Negative / Trade-offs
- Ties us to Amplify Hosting's pricing and feature set; migration off would
  require re-registering callback URLs.
- Staging bucket adds a small amount of S3 state to manage (cleaned up with
  30-day lifecycle on deploy artifacts, 90-day on access logs).

### Neutral
- Custom domains, if later required, are configured in the Amplify console
  and do not affect this ADR's decision.

## Implementation Notes

- `infra-cdk/lib/amplify-hosting-stack.ts` — Amplify app, `main` branch,
  staging S3 bucket with SSL-only policy and access logging.
- `infra-cdk/lib/fast-main-stack.ts` — passes `amplifyUrl` into Cognito
  (`callbackUrls`) and Backend (`frontendUrl`) before synth.
- `scripts/deploy-frontend.py` — cross-platform deploy script that builds
  Vite and pushes to the staging bucket.

## References

- Internal: `docs/DEPLOYMENT.md`, `frontend/README`, `Makefile`
- External: [AWS Amplify Hosting](https://docs.aws.amazon.com/amplify/latest/userguide/welcome.html)
