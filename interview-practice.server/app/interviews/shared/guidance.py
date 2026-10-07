"""Wording that describes an Interview's role, difficulty and tone to the model.

Shared by every prompt that has to speak about them (plan, conversation, suggestions).
"""

from app.models import Difficulty, InterviewerRole, Tone

# Keyed by the `InterviewerRole` / `Tone` members, looked up with the plain strings an
# Interview stores; tests/test_interview_vocabulary.py checks every member is covered.
ROLE_GUIDANCE: dict[str, str] = {
    InterviewerRole.recruiter: (
        "First-contact screen. Shallow technical and company knowledge; mostly broad "
        "background and motivation questions, plus logistics (salary expectations, "
        "availability, work authorization, remote/hybrid preference). Not an engineer: "
        "never asks low-level technical or coding questions, only what a recruiter "
        "would ask (technologies used, depth of experience at a high level). Typical "
        'titles: "Talent Acquisition Partner", "Technical Recruiter".'
    ),
    InterviewerRole.technical_screener: (
        "The first technical interview. Real technical depth, rigorous and critical. "
        "The title is an engineering role in the candidate's domain."
    ),
    InterviewerRole.hr: (
        "Culture, values and soft-skills fit; procedural in tone. Not an engineer: "
        "asks about teamwork, conflict, motivation, working style, salary and notice "
        "period, never about low-level technical details. Typical titles: "
        '"HR Business Partner", "People Operations Manager".'
    ),
    InterviewerRole.hiring_manager: (
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
TONE_GUIDANCE: dict[str, str] = {
    Tone.strict: "demanding, precise and critical",
    Tone.neutral: "professional and even-handed",
    Tone.friendly: "warm, encouraging and conversational",
}
