# ADR-0013: Enforce civic-domain guardrails via structured prompt injection

- **Status:** Accepted
- **Date:** 2026-04-29
- **Deciders:** Maplewood Civic Services team, Security
- **Tags:** guardrails, prompt, safety

## Context

A city-services agent must refuse to answer questions that look civic
but are outside Maplewood's remit: legal advice, medical advice,
financial/tax advice, political opinions, emergencies requiring 911,
etc. Getting this wrong is a reputational and (potentially) legal
problem for the city. We need guardrails that are:

- **Declarative and reviewable** — legal and comms should be able to
  read and sign off on the rules without reading code.
- **Close to the prompt** — the guardrails should appear inside the
  system prompt so the model treats them as first-class instructions,
  not as a filter run against outputs.
- **Domain-specific refusals** — each category has its own wording
  that points the citizen to the right office (City Attorney, etc.).

Options like Amazon Bedrock Guardrails handle generic toxicity and
denied topics well but are less well-suited to the "refuse-and-redirect"
patterns Maplewood needs today.

## Decision

Maintain a structured `GUARDRAIL_RULES` catalog in `gateway/guardrails/`:

- `models.py` — `GuardrailCategory` enum plus a `GuardrailRule`
  dataclass (`description`, `detection_hints`, `response_template`).
- `rules.py` — the canonical rule catalog (legal advice, medical
  advice, financial advice, political opinions, emergencies, etc.).
- `prompt.py::generate_prompt_block` — renders the rules into a
  markdown block the agent pattern injects into its system prompt.
- `refusal.py` — helpers for constructing refusal responses when a
  rule is matched out-of-band.

Agent patterns call `generate_prompt_block` and concatenate its output
into their `SYSTEM_PROMPT`. Rule changes ship as normal code reviews.

## Alternatives Considered

- **Amazon Bedrock Guardrails policies.** Rejected as sole mechanism:
  the "refuse-and-redirect" templates are specific enough that
  maintaining them as code is clearer. Bedrock Guardrails remains a
  candidate for layered defense against generic content categories.
- **Post-hoc output moderation.** Rejected: late to catch unsafe
  advice that is already partially streamed to the user.
- **Rules in a database / admin UI.** Rejected (for now): premature
  and moves policy out of code review.
- **Free-form guidance in the system prompt.** Rejected: not
  reviewable, easy to drift, and hard to test.

## Consequences

### Positive
- Rules are data, not prose — easy to diff, review, and test.
- Each category carries its own refusal template, giving consistent
  citizen-facing phrasing.
- Works across agent frameworks because it's plain text injected into
  the prompt.
- Leaves room to layer Bedrock Guardrails on top later without
  restructuring the code.

### Negative / Trade-offs
- Prompt-injection resistance is only as good as the model's
  adherence to its system prompt; a determined adversarial input may
  still slip through.
- Long prompt blocks cost tokens on every turn. Keep rules concise
  and prune hints that aren't pulling their weight.
- No runtime enforcement if the model ignores the rule — needs
  monitoring and an eval harness (separate work).

### Neutral
- Rules are static code today; rotating them requires a deploy. Fine
  for v1.

## Implementation Notes

- `gateway/guardrails/models.py` — `GuardrailCategory`,
  `GuardrailRule`.
- `gateway/guardrails/rules.py` — authoritative rule catalog.
- `gateway/guardrails/prompt.py::generate_prompt_block` —
  system-prompt renderer.
- Agent patterns (e.g. `patterns/strands-single-agent/basic_agent.py`)
  should call `generate_prompt_block()` during `SYSTEM_PROMPT`
  construction.

## References

- Internal: `gateway/guardrails/README` (if present), `CLAUDE.md`
  (scope of the civic domain).
- External: [Amazon Bedrock Guardrails](https://docs.aws.amazon.com/bedrock/latest/userguide/guardrails.html)
  — candidate complementary control.
