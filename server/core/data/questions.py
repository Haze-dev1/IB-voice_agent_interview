"""Interview question bank for investment banking practice interviews.

Static question content organized by category. Each question has a text prompt,
category label, and expected key points for answer evaluation.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class InterviewQuestion:
    """A single interview question with metadata.

    Args:
        id: Unique identifier for the question.
        text: The question text spoken to the candidate.
        category: Question category (technical or behavioral).
        key_points: Key points a strong answer should cover.
        follow_up_hint: Optional hint for generating follow-up questions.
    """

    id: str
    text: str
    category: str
    key_points: list[str] = field(default_factory=list)
    follow_up_hint: str = ""


TECHNICAL_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(
        id="tech_dcf_depreciation",
        text=(
            "Walk me through how a 10 dollar increase in depreciation expense "
            "affects the three financial statements."
        ),
        category="technical",
        key_points=[
            "Income statement: EBIT decreases by 10, taxable income decreases by 10",
            "Tax shield: taxes decrease by 10 times the tax rate (e.g. 2.1 at 21%)",
            "Cash flow statement: net income decreases by 7.9, add back 10 depreciation = +2.1 cash",
            "Balance sheet: PP&E decreases by 10 (accumulated depreciation), "
            "retained earnings decreases by 7.9, cash increases by 2.1",
        ],
        follow_up_hint="Ask about the difference between cash and accrual impact.",
    ),
    InterviewQuestion(
        id="tech_dcf_wacc",
        text=(
            "Explain what WACC is and when you would use it in a DCF valuation."
        ),
        category="technical",
        key_points=[
            "WACC is weighted average cost of capital",
            "Blends cost of equity and after-tax cost of debt",
            "Used as discount rate for unlevered free cash flows",
            "Reflects the risk of the business and its capital structure",
        ],
        follow_up_hint="Ask about how WACC changes with leverage.",
    ),
    InterviewQuestion(
        id="tech_lbo_basics",
        text=(
            "What are the key characteristics of a good LBO candidate?"
        ),
        category="technical",
        key_points=[
            "Stable and predictable cash flows",
            "Strong market position or competitive advantage",
            "Low existing leverage or under-levered balance sheet",
            "Identifiable value creation opportunities",
            "Clear exit path within 3 to 7 years",
        ],
        follow_up_hint="Ask about how management incentives align with sponsors.",
    ),
    InterviewQuestion(
        id="tech_multiples",
        text=(
            "When would you use an EV to EBITDA multiple versus a P to E ratio "
            "for valuation?"
        ),
        category="technical",
        key_points=[
            "EV EBITDA is enterprise-level, capital structure neutral",
            "P to E is equity-level, affected by leverage",
            "EV EBITDA better for comparing companies with different debt levels",
            "P to E more appropriate for financial institutions or stable earnings",
        ],
        follow_up_hint="Ask about sector-specific multiples.",
    ),
    InterviewQuestion(
        id="tech_accounting_linkage",
        text=(
            "If a company pays 50 million to acquire another firm, walk me through "
            "how this shows up on the financial statements."
        ),
        category="technical",
        key_points=[
            "Balance sheet: cash decreases by 50 (or debt increases), "
            "goodwill and intangibles increase",
            "If asset purchase, step-up basis affects depreciation",
            "Income statement: deal fees hit as one-time expense, "
            "future amortization of intangibles reduces earnings",
            "Cash flow statement: investing outflow of 50",
        ],
        follow_up_hint="Ask about goodwill impairment testing.",
    ),
]

BEHAVIORAL_QUESTIONS: list[InterviewQuestion] = [
    InterviewQuestion(
        id="behav_why_banking",
        text="Why investment banking? What draws you to this career?",
        category="behavioral",
        key_points=[
            "Genuine interest in financial markets and deal execution",
            "Desire to work on impactful transactions",
            "Interest in learning from experienced professionals",
            "Willingness to work hard and commit to the lifestyle",
        ],
        follow_up_hint="Ask about specific deals or transactions that interest them.",
    ),
    InterviewQuestion(
        id="behav_resume",
        text="Walk me through your resume.",
        category="behavioral",
        key_points=[
            "Clear narrative connecting past experiences to banking",
            "Highlights relevant skills: analytical, quantitative, teamwork",
            "Shows progression and learning",
            "Demonstrates why banking is the next logical step",
        ],
        follow_up_hint="Ask about a specific challenge from their experience.",
    ),
    InterviewQuestion(
        id="behav_teamwork",
        text=(
            "Tell me about a time you had to work with a difficult team member. "
            "How did you handle it?"
        ),
        category="behavioral",
        key_points=[
            "Uses STAR format: Situation, Task, Action, Result",
            "Shows emotional intelligence and professionalism",
            "Demonstrates ability to find common ground",
            "Reflects on what they learned from the experience",
        ],
        follow_up_hint="Ask about the outcome and what they would do differently.",
    ),
    InterviewQuestion(
        id="behav_stress",
        text=(
            "How do you handle working under pressure with tight deadlines?"
        ),
        category="behavioral",
        key_points=[
            "Specific example of working under pressure",
            "Prioritization and time management approach",
            "Communication with stakeholders about deadlines",
            "Maintaining quality while working fast",
        ],
        follow_up_hint="Ask about a specific high-pressure situation.",
    ),
]

ALL_QUESTIONS = TECHNICAL_QUESTIONS + BEHAVIORAL_QUESTIONS

QUESTION_BY_ID = {q.id: q for q in ALL_QUESTIONS}


def get_question_by_id(question_id: str) -> InterviewQuestion | None:
    """Look up a question by its unique ID.

    Args:
        question_id: The question identifier.

    Returns:
        The matching InterviewQuestion, or None if not found.
    """
    return QUESTION_BY_ID.get(question_id)


def get_technical_questions() -> list[InterviewQuestion]:
    """Return all technical interview questions.

    Returns:
        List of technical InterviewQuestion instances.
    """
    return TECHNICAL_QUESTIONS.copy()


def get_behavioral_questions() -> list[InterviewQuestion]:
    """Return all behavioral interview questions.

    Returns:
        List of behavioral InterviewQuestion instances.
    """
    return BEHAVIORAL_QUESTIONS.copy()
