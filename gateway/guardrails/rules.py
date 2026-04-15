"""Guardrail rule definitions for the Maplewood Civic Services Agent.

Each rule is structured data describing a restricted topic category, detection
hints for identifying it, and a response template for polite refusal.
"""

from gateway.guardrails.models import GuardrailCategory, GuardrailRule

GUARDRAIL_RULES: dict[GuardrailCategory, GuardrailRule] = {
    GuardrailCategory.LEGAL_ADVICE: GuardrailRule(
        category=GuardrailCategory.LEGAL_ADVICE,
        description=(
            "The agent must not provide legal advice, interpret statutes or "
            "ordinances, or offer opinions on legal liability. Citizens should "
            "be directed to the City Attorney's office."
        ),
        detection_hints=[
            "is this legal",
            "can I sue",
            "my legal rights",
            "legal advice",
            "liability",
            "ordinance interpretation",
            "sue the city",
            "legal obligation",
            "statute of limitations",
        ],
        response_template=(
            "I'm not able to provide legal advice or interpret city ordinances. "
            "For legal questions, I'd recommend contacting the Maplewood City "
            "Attorney's office at (555) 555-0100 or visiting City Hall, Room 201. "
            "They can help you with your specific situation."
        ),
    ),
    GuardrailCategory.TIMELINE_PROMISES: GuardrailRule(
        category=GuardrailCategory.TIMELINE_PROMISES,
        description=(
            "The agent must not promise or guarantee specific timelines for "
            "permits, inspections, reviews, or other city processes. Processing "
            "times vary and only the responsible department can give estimates."
        ),
        detection_hints=[
            "how long will it take",
            "when will my permit",
            "guarantee timeline",
            "promise me",
            "exact date",
            "how many days until",
            "when will I hear back",
            "deadline for approval",
        ],
        response_template=(
            "I'm not able to guarantee specific timelines for city processes, as "
            "processing times can vary based on several factors. For the most "
            "accurate estimate on your request, please contact the relevant "
            "department directly. I can help you find the right contact "
            "information if you'd like."
        ),
    ),
    GuardrailCategory.CODE_ENFORCEMENT_COMPLAINTS: GuardrailRule(
        category=GuardrailCategory.CODE_ENFORCEMENT_COMPLAINTS,
        description=(
            "Code enforcement complaints (e.g., property violations, noise "
            "complaints, zoning violations by neighbors) involve sensitive "
            "neighbor relations and potential legal action. These must be "
            "escalated to the Code Enforcement Division for proper handling."
        ),
        detection_hints=[
            "neighbor's property",
            "code violation",
            "report a violation",
            "property complaint",
            "noise complaint",
            "abandoned vehicle",
            "overgrown yard",
            "illegal construction",
            "zoning violation by neighbor",
            "junk cars",
        ],
        response_template=(
            "I understand your concern. Code enforcement complaints need to be "
            "handled directly by our Code Enforcement Division to ensure proper "
            "documentation and follow-up. You can file a complaint by calling "
            "(555) 555-0120 or visiting the Code Enforcement office at City Hall, "
            "Room 105. Complaints can also be submitted anonymously."
        ),
    ),
    GuardrailCategory.ADA_REQUESTS: GuardrailRule(
        category=GuardrailCategory.ADA_REQUESTS,
        description=(
            "Americans with Disabilities Act (ADA) accommodation requests and "
            "accessibility complaints require specialized handling to ensure "
            "compliance with federal law. These must be routed to the ADA "
            "Coordinator."
        ),
        detection_hints=[
            "ADA",
            "disability accommodation",
            "wheelchair accessible",
            "accessibility",
            "reasonable accommodation",
            "disability rights",
            "handicap access",
            "service animal",
            "assistive technology",
        ],
        response_template=(
            "Accessibility and ADA accommodation requests are very important to "
            "the City of Maplewood. To ensure your request is properly handled, "
            "please contact our ADA Coordinator directly at (555) 555-0130 or "
            "email ada@maplewood.gov. They can assist with accommodation requests "
            "and address any accessibility concerns."
        ),
    ),
    GuardrailCategory.GENERAL_SENSITIVE: GuardrailRule(
        category=GuardrailCategory.GENERAL_SENSITIVE,
        description=(
            "Catch-all for other sensitive topics that require human judgment, "
            "including personnel matters, discrimination complaints, emergency "
            "situations, and requests involving personal safety."
        ),
        detection_hints=[
            "discrimination",
            "harassment",
            "emergency",
            "personal safety",
            "threat",
            "personnel complaint",
            "employee misconduct",
            "whistleblower",
            "retaliation",
            "civil rights",
        ],
        response_template=(
            "This sounds like a matter that needs personal attention from our "
            "staff. For sensitive concerns, please contact the City Manager's "
            "office at (555) 555-0110 or visit City Hall during business hours "
            "(Monday-Friday, 8 AM - 5 PM). If this is an emergency, please "
            "call 911."
        ),
    ),
}


def get_rule(category: GuardrailCategory) -> GuardrailRule:
    """Return the guardrail rule for a given category.

    Args:
        category: The guardrail category to look up.

    Returns:
        The GuardrailRule for the requested category.

    Raises:
        KeyError: If the category is not found in the rules.
    """
    return GUARDRAIL_RULES[category]
