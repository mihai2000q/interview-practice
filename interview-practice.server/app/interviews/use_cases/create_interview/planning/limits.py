"""Caps on the text the plan calls return, so one runaway reply can't bloat a row."""

MAX_TEXT_CHARS = 500


def plan_size(target: int) -> int:
    """How many questions the plan holds for an interview of `target` questions: the
    target, plus reserves the interviewer can swap in when a planned question no longer
    fits (the candidate already covered it, or turned hostile). A short interview gets
    up to twice as many, a long one proportionally fewer extra, so the reply stays
    manageable: 5 -> 10, 8 -> 13, 10 -> 15, 20 -> 28, 30 -> 41."""
    reserves = min(target, 5 + round(0.3 * max(0, target - 10)))
    return target + reserves
