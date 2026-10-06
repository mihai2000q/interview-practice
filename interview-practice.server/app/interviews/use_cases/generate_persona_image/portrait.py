"""The persona's portrait image (docs/architecture.md, "Persona image generation").

Generated once, when the session page asks for it, and stored on disk under `instance/`,
so Results and the history sidebar can show it without another API call. The portrait is
cosmetic: nothing else waits for it.
"""

import logging
import uuid
from pathlib import Path

from app.llm.openrouter import GeneratedImage
from app.paths import instance_dir

logger = logging.getLogger(__name__)

_SUBDIR = Path("uploads") / "personas"
_EXPRESSIONS = {
    "strict": "a serious, composed expression",
    "neutral": "a calm, professional expression",
    "friendly": "a warm, approachable smile",
}


def build_prompt(name: str, title: str, tone: str) -> str:
    expression = _EXPRESSIONS.get(tone, _EXPRESSIONS["neutral"])
    return (
        f"A realistic professional headshot photograph of {name}, a {title}. "
        "Head and shoulders, facing the camera, plain softly blurred office "
        f"background, natural light, {expression}. "
        "A fictional person, not a real public figure. Square framing. "
        "No text, no logo, no watermark."
    )


def store_portrait(image: GeneratedImage) -> str | None:
    """Write the image under `instance/` and return its path relative to it.

    None if it can't be written (full or read-only volume).
    """
    relative = _SUBDIR / f"{uuid.uuid4()}.{image.extension}"
    absolute = instance_dir() / relative
    try:
        absolute.parent.mkdir(parents=True, exist_ok=True)
        absolute.write_bytes(image.data)
    except OSError:
        logger.exception("Could not store the persona portrait")
        return None
    return str(relative)


def delete_portrait(relative_path: str) -> None:
    (instance_dir() / relative_path).unlink(missing_ok=True)
