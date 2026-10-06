"""The security guard: every piece of untrusted text passes through here before it is
put in a prompt (docs/architecture.md, "Security guard").

Heuristic only. OWASP is explicit that input filtering alone can't stop prompt
injection, so this is one layer next to `fence` (isolating untrusted text inside the
prompt) and the structured-output validation in the client. It is tuned to catch
blatant attempts and their cheap disguises while leaving ordinary CVs, job
descriptions and interview answers alone. Known trade-off: bare "developer mode" is
allowed, because mobile developers write about it legitimately.

How a check works:
1. The length is checked first, so the scan below always runs on bounded input.
2. The text is turned into a few normalized "views" (see `_views`) that undo the usual
   disguises: invisible characters, accents, look-alike letters, leetspeak, spaced-out
   letters.
3. Every rule runs on every view; the first match rejects the text.
"""

import logging
import re
import unicodedata
from dataclasses import dataclass

from pydantic import AfterValidator
from pydantic_core import PydanticCustomError

from app.errors.exceptions import InputRejectedError

logger = logging.getLogger(__name__)

# Per-kind length limits, in characters (callers pass one as `max_length`).
MAX_FIELD_CHARS = 500
# A chat message: the candidate's reply, and the length the interviewer is asked to
# stay under too.
MAX_MESSAGE_CHARS = 2_000
MAX_DOCUMENT_CHARS = 50_000
# Nothing may ask for more than this: it bounds the scan cost per request.
HARD_MAX_CHARS = 100_000

# What the candidate sees. Says nothing about which rule matched, so the patterns
# can't be probed; the category goes to the server log instead.
REJECTION_MESSAGE = (
    "This text contains wording we can't pass to the interviewer, such as "
    "instructions aimed at the AI. Please rephrase it and try again."
)
EXCERPT_MAX_CHARS = 80


@dataclass(frozen=True)
class _Rule:
    category: str
    pattern: re.Pattern[str]


def _rule(category: str, *patterns: str) -> _Rule:
    return _Rule(category, re.compile("|".join(patterns)))


def _gap(max_words: int) -> str:
    """Separator, then up to `max_words` filler words each followed by a separator."""
    return rf"\W+(?:\w+\W+){{0,{max_words}}}"


_OVERRIDE_VERBS = r"(?:ignore|disregard|forget|override|overrule|discard)"
_EXTRACT_VERBS = (
    r"(?:reveal|show|print|repeat|output|display|leak|dump|expose|disclose)"
)
_INSTRUCTION_NOUNS = r"(?:instructions?|prompts?|rules|directions|guidelines)"
_PRIOR_QUALIFIERS = (
    r"(?:previous|prior|above|earlier|preceding|your|system|original|initial)"
)
_DANGEROUS_PERSONAS = r"(?:dan|unrestricted|unfiltered|uncensored|jailbroken|evil)"
_MODE_NAMES = r"god|jailbreak(?:ed)?|sudo|unrestricted|dan"

# Matched against the views from `_views`: lowercase, accent-free, whitespace
# collapsed to single spaces. Categories follow OpenRouter's own guardrail, plus
# `verdict_manipulation` for this app's own target (the hire/no-hire evaluation).
_RULES = (
    _rule(
        "instruction_override",
        # "ignore (all) previous instructions", "disregard the system prompt"
        rf"\b{_OVERRIDE_VERBS}{_gap(3)}{_PRIOR_QUALIFIERS}{_gap(1)}{_INSTRUCTION_NOUNS}\b",
        # "ignore the instructions above"
        rf"\b(?:ignore|disregard|forget|discard){_gap(2)}{_INSTRUCTION_NOUNS}"
        rf"{_gap(2)}(?:above|preceding)\b",
        # "ignore everything above", "disregard the above"
        r"\b(?:ignore|disregard|forget|discard)\W+(?:(?:the|all|everything|anything)\W+)"
        r"{1,3}(?:above|preceding)\b",
        # "forget everything you were told"
        r"\b(?:ignore|disregard|forget)\W+(?:everything|anything|all)\W+"
        r"(?:you\W+(?:were|have been|are)\W+(?:told|taught|given)|you know)\b",
        # "new instructions: ..."
        r"\b(?:new|updated|revised|real|actual|additional)\s+(?:system\s+)?"
        r"instructions?\s*:",
    ),
    _rule(
        "mode_activation",
        rf"\b(?:{_MODE_NAMES}|dev(?:eloper)?)[ -]?mode\s+"
        r"(?:enabled|activated|engaged)\b",
        r"\b(?:enable|enter|activate|engage|switch to|you are (?:now )?in)\s+"
        rf"(?:the\s+)?(?:{_MODE_NAMES})[ -]?mode\b",
    ),
    _rule(
        "prompt_extraction",
        rf"\b{_EXTRACT_VERBS}{_gap(3)}(?:system|hidden|initial|original|internal|"
        r"secret|developer)\s+(?:prompt|instructions?|message)\b",
        rf"\b{_EXTRACT_VERBS}{_gap(2)}your\s+(?:prompt|instructions|rules|guidelines)\b",
    ),
    _rule(
        "role_manipulation",
        r"\byou(?:'re| are)\s+(?:now\s+)?(?:no longer|not)\s+"
        r"(?:bound|restricted|limited|an? (?:ai|interviewer))\b",
        r"\b(?:you(?:'re| are)|act as|acting as|pretend to be|"
        r"pretend (?:that )?you(?:'re| are)|behave as|roleplay as)\s+(?:now\s+)?"
        rf"(?:an?\s+)?{_DANGEROUS_PERSONAS}\b",
        r"\bfrom now on,?\s+(?:you\s+(?:will|must|should|shall|are|respond|answer|"
        r"reply|speak|behave|obey)|ignore|act|respond|only|always)\b",
        r"\bpretend (?:that )?you (?:are|have) no\b",
    ),
    _rule("dan_jailbreak", r"\bdo anything now\b", r"\bdan[ -]?mode\b"),
    _rule(
        "safety_bypass",
        r"\b(?:disable|bypass|turn off|remove|circumvent|evade)"
        rf"{_gap(3)}(?:safety|content|security|moderation)\s+"
        r"(?:filters?|guidelines|restrictions|polic(?:y|ies)|checks?|guardrails?)\b",
    ),
    _rule(
        "verdict_manipulation",
        # "rate me 10/10", "give me a perfect score", "give me a strong hire"
        r"\b(?:rate|score|grade|mark|evaluate|give)\s+me\s+(?:an?\s+)?(?:\w+\s+){0,2}"
        r"(?:10\s*/\s*10|5\s*/\s*5|100\s*%|perfect|highest|full marks|hire)\b",
        r"\bverdict\s*(?:is|=|:)\s*(?:strong\s+)?hire\b",
    ),
    _rule(
        "tag_injection",
        # `(?<!\w)` keeps generics such as `List<User>` out; a real fake role tag
        # stands on its own.
        r"(?<!\w)<\s*(?:system|assistant|user|instructions?)\s*>",
        r"</\s*(?:system|assistant|user|instructions?)\s*>",
        r"\[/?(?:inst|system)\]|<<\s*/?sys\s*>>",
    ),
    _rule("control_token", r"<\|[a-z_]{2,30}\|>"),
)

# Letters that look like Latin ones. NFKD handles compatibility forms (fullwidth,
# accents); these are different letters that merely look alike.
_CONFUSABLES = {
    ord(src): dst
    for src, dst in zip(
        "асеорухіјѕһкмтαεικνορτυχ’‘`",  # noqa: RUF001
        "aceopyxijshkmtaeikvoptux'''",
        strict=True,
    )
}
_LEET = str.maketrans("013457@$", "oieastas")

_WHITESPACE = re.compile(r"\s+")
# "i g n o r e", "i.g.n.o.r.e", "i-g-n-o-r-e": four or more single characters.
_SPACED_LETTERS = re.compile(
    r"(?<![a-z0-9])(?:[a-z0-9][ .\-_*]){3,}[a-z0-9](?![a-z0-9])"
)
_LETTER_SEPARATORS = re.compile(r"[ .\-_*]")


def _is_invisible(char: str) -> bool:
    # Control, format (zero-width, bidi, ...), private-use and unassigned characters.
    return unicodedata.category(char)[0] == "C"


def _views(text: str) -> list[str]:
    """Normalized forms of `text` for the rules to run on (duplicates removed)."""
    decomposed = unicodedata.normalize("NFKD", text)
    folded = "".join(
        c for c in decomposed if unicodedata.category(c) not in ("Mn", "Me")
    )
    folded = folded.casefold().translate(_CONFUSABLES)

    # An invisible character may sit inside a word ("ig<ZWSP>nore") or stand in for a
    # space ("ignore<ZWSP>all"), so try both readings.
    spaced = _WHITESPACE.sub(
        " ", "".join(" " if _is_invisible(c) else c for c in folded)
    )
    joined = _WHITESPACE.sub(" ", "".join(c for c in folded if not _is_invisible(c)))
    collapsed = _SPACED_LETTERS.sub(
        lambda m: _LETTER_SEPARATORS.sub("", m.group()), spaced
    )
    leet = spaced.translate(_LEET)
    return list(dict.fromkeys([spaced, joined, collapsed, leet]))


def check_text(text: str, *, max_length: int) -> None:
    """Raise `InputRejectedError` (422) if `text` is too long or looks like injection.

    For injection, `details` carries a short `excerpt` of the wording that matched, so
    the candidate can find and rephrase it in a long document.
    """
    if max_length > HARD_MAX_CHARS:
        raise ValueError(f"max_length may not exceed {HARD_MAX_CHARS}")
    if len(text) > max_length:
        raise InputRejectedError(
            f"This text is too long (limit {max_length:,} characters).",
            details={"reason": "too_long", "maxLength": max_length},
        )
    for view in _views(text):
        for rule in _RULES:
            match = rule.pattern.search(view)
            if match:
                # Category only: never log the text itself, it may be a private CV.
                logger.warning("Guard rejected text: %s", rule.category)
                raise InputRejectedError(
                    REJECTION_MESSAGE,
                    details={
                        "reason": "prompt_injection",
                        "excerpt": match.group()[:EXCERPT_MAX_CHARS],
                    },
                )


def guarded(max_length: int = MAX_FIELD_CHARS) -> AfterValidator:
    """Pydantic validator that runs `check_text` on a string field.

    Use it in `Annotated[str, guarded()]`. A rejection becomes a validation error of
    type `input_rejected`, which the error handler turns into a 422 `INPUT_REJECTED`
    whose `details.field` is the field's own name (taken from the error location, so
    nothing is hardcoded).
    """

    def validate(value: str) -> str:
        try:
            check_text(value, max_length=max_length)
        except InputRejectedError as exc:
            raise PydanticCustomError(
                "input_rejected", exc.message, exc.details
            ) from exc
        return value

    return AfterValidator(validate)


def fence(label: str, text: str) -> str:
    """Wrap untrusted text in `<label>` tags for the prompt.

    The system prompt should tell the model that everything inside is data, never
    instructions. Every angle bracket in the text is escaped (after folding fullwidth
    and similar forms to plain ones), so no spelling of a closing tag can end the
    fence early.
    """
    safe = unicodedata.normalize("NFKC", text).replace("<", "&lt;").replace(">", "&gt;")
    return f"<{label}>\n{safe}\n</{label}>"
