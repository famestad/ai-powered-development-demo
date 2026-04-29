# Guardrails

The `gateway.guardrails` module provides structured guardrail rules, refusal
response building, and system-prompt injection for the Maplewood Civic Services
Agent. It's designed to be importable by both the Strands and LangGraph agent
patterns.

Use it to keep the agent from answering questions it shouldn't — legal advice,
timeline guarantees, code-enforcement complaints, ADA accommodation requests,
and other sensitive topics — and instead route citizens to the right human
contact.

## Categories

Five categories are defined. Each maps to a `GuardrailRule` with a description,
detection hints, and a citizen-facing response template.

| Category | Covers | Redirects to |
| --- | --- | --- |
| `LEGAL_ADVICE` | Legal questions, ordinance interpretation, liability | City Attorney's office — (555) 555-0100 |
| `TIMELINE_PROMISES` | Guaranteed timelines for permits, inspections, reviews | The relevant department |
| `CODE_ENFORCEMENT_COMPLAINTS` | Property violations, noise, zoning complaints | Code Enforcement Division — (555) 555-0120 |
| `ADA_REQUESTS` | Accessibility and ADA accommodation requests | ADA Coordinator — (555) 555-0130, ada@maplewood.gov |
| `GENERAL_SENSITIVE` | Discrimination, harassment, personnel, personal safety | City Manager's office — (555) 555-0110 (or 911 for emergencies) |

## Public API

All public symbols are re-exported from `gateway.guardrails`:

```python
from gateway.guardrails import (
    GuardrailCategory,
    GuardrailRule,
    RefusalResponse,
    GUARDRAIL_RULES,
    get_rule,
    build_refusal_response,
    generate_prompt_block,
)
```

### Models

**`GuardrailCategory`** — `str` enum with the five category values above.

**`GuardrailRule`** — Pydantic model describing one category:

- `category: GuardrailCategory`
- `description: str` — human-readable explanation
- `detection_hints: list[str]` — example phrases that indicate this category
- `response_template: str` — refusal message template (may contain a
  `{redirect}` placeholder)

**`RefusalResponse`** — the structured refusal returned to the caller:

- `citizen_message: str` — the polite, citizen-facing text
- `reason: str` — internal reason suitable for logging and audit
- `category: GuardrailCategory`

### Rule lookup

```python
from gateway.guardrails import GUARDRAIL_RULES, GuardrailCategory, get_rule

rule = get_rule(GuardrailCategory.LEGAL_ADVICE)
print(rule.description)
print(rule.detection_hints)
```

`GUARDRAIL_RULES` is a `dict[GuardrailCategory, GuardrailRule]` containing all
five rules. `get_rule(category)` returns the matching rule or raises
`KeyError` if the category is unknown.

### Building a refusal response

Use `build_refusal_response` when the agent (or a classifier) determines a
message matches a guardrail category. It returns a `RefusalResponse` with the
citizen-facing message, an internal reason, and the category.

```python
from gateway.guardrails import build_refusal_response, GuardrailCategory

response = build_refusal_response(GuardrailCategory.ADA_REQUESTS)

# Send to the citizen
print(response.citizen_message)
# "Accessibility and ADA accommodation requests are very important..."

# Log for audit
logger.info(
    "guardrail_refusal",
    category=response.category.value,
    reason=response.reason,
)
```

### Injecting rules into a system prompt

`generate_prompt_block` formats the active guardrail rules as a Markdown
section suitable for appending to an agent's system prompt. Pass a subset of
categories to limit what's included; pass `None` (or omit the argument) to
include all five.

```python
from gateway.guardrails import generate_prompt_block, GuardrailCategory

# All five categories
full_block = generate_prompt_block()

# Only a subset
partial_block = generate_prompt_block(
    categories=[
        GuardrailCategory.LEGAL_ADVICE,
        GuardrailCategory.ADA_REQUESTS,
    ]
)

system_prompt = f"{base_prompt}\n\n{full_block}"
```

The output begins with a `## Guardrails` header and a `MUST`-directive
instruction, followed by one `### <CATEGORY>` block per rule containing the
description, detection hints, and required response.

## Example: end-to-end usage

```python
from gateway.guardrails import (
    GuardrailCategory,
    build_refusal_response,
    generate_prompt_block,
)

# 1. At agent startup: build the system prompt
system_prompt = BASE_PROMPT + "\n\n" + generate_prompt_block()

# 2. At request time: if a classifier decides the message is legal advice,
#    short-circuit the model call and return the canned refusal.
def handle_refusal(category: GuardrailCategory) -> dict:
    refusal = build_refusal_response(category)
    logger.info("guardrail_triggered", reason=refusal.reason)
    return {"message": refusal.citizen_message}
```

## Extending the rules

All rules live in [`gateway/guardrails/rules.py`](../gateway/guardrails/rules.py)
as a single `GUARDRAIL_RULES` dict. To add or modify a category:

1. Add a value to `GuardrailCategory` in `gateway/guardrails/models.py`.
2. Add the corresponding `GuardrailRule` entry to `GUARDRAIL_RULES`.
3. Add an internal reason string to `_CATEGORY_REASONS` in
   `gateway/guardrails/refusal.py`.
4. Add tests to `tests/unit/test_guardrails.py` covering the new category
   (the existing parametrized tests will automatically exercise most paths
   once `ALL_CATEGORIES` is updated).

Keep response templates polite, specific, and actionable — every refusal
should tell the citizen who to contact instead.

## Source

- Module: [`gateway/guardrails/`](../gateway/guardrails/)
- Tests: [`tests/unit/test_guardrails.py`](../tests/unit/test_guardrails.py)
- Introduced in: [#18](https://github.com/famestad/ai-powered-development-demo/pull/18)
  (closes [#15](https://github.com/famestad/ai-powered-development-demo/issues/15))
