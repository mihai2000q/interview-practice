"""Caps on the text the plan calls return, so one runaway reply can't bloat a row."""

MAX_TEXT_CHARS = 500


def plan_range(target: int) -> tuple[int, int]:
    """The fewest and most questions the plan may hold for an interview of `target`
    questions: the target plus reserves the interviewer can swap in when a planned
    question no longer fits (the candidate already covered it, or turned hostile).
    There are at least 3 reserves and at most `3 + target/4`, never more than the
    target itself: 5 -> 8 to 9, 10 -> 13 to 15, 20 -> 23 to 28, 30 -> 33 to 41."""
    most = min(target, 3 + round(target / 4))
    return target + min(3, most), target + most
