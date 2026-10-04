"""Wording that describes an Interview's role, difficulty and tone to the model.

Shared by every prompt that has to speak about them (plan, conversation, suggestions).
"""

from app.models import Difficulty

ROLE_GUIDANCE = {
    "recruiter": (
        "First-contact screen. Shallow technical and company knowledge; mostly broad "
        "background and motivation questions, plus logistics (salary expectations, "
        "availability, work authorization, remote/hybrid preference). Typical titles: "
        '"Talent Acquisition Partner", "Technical Recruiter".'
    ),
    "technical_screener": (
        "The first technical interview. Real technical depth, rigorous and critical. "
        "The title is an engineering role in the candidate's domain."
    ),
    "hr": (
        "Culture, values and soft-skills fit; procedural in tone. Typical titles: "
        '"HR Business Partner", "People Operations Manager".'
    ),
    "hiring_manager": (
        "The final stage. Real technical depth plus organizational context: ownership, "
        "collaboration, how the candidate would work in the team. The title is a "
        "manager role in the candidate's domain."
    ),
}
DIFFICULTY_GUIDANCE = {
    Difficulty.easy.value: "fundamentals and straightforward questions",
    Difficulty.medium.value: "applied questions with some follow-up depth",
    Difficulty.hard.value: (
        "deep, probing questions: trade-offs, edge cases, failure modes"
    ),
}
TONE_GUIDANCE = {
    "strict": "demanding, precise and critical",
    "neutral": "professional and even-handed",
    "friendly": "warm, encouraging and conversational",
}
