from sqlalchemy import inspect

from app.errors.exceptions import BadRequestError
from app.extensions import db
from app.llm.phase_settings import (
    PhaseConfig,
    ensure_judge_differs_from_interviewer,
    ensure_model_allowed,
    ensure_reasoning_effort_allowed,
    phase_defaults,
)
from app.llm.schemas import PhaseSettings, PhaseSettingsOverride
from app.models import GenerationPhase, PreferencePhaseSettings
from app.services.preferences import load_preferences, lock_preferences


def update_preferences(
    body: PhaseSettingsOverride,
) -> dict[GenerationPhase, PhaseConfig]:
    """Change the defaults of the phases the body names, leaving the others alone.

    A setting sent as null goes back to the built-in default, and a phase sent as null
    goes back to the built-in defaults entirely. The judge rule (ADR 0009) is checked
    on the defaults as they will be, so models can be swapped in one request.
    """
    changes = {
        GenerationPhase(name): getattr(body, name) for name in body.model_fields_set
    }
    if not changes:
        raise BadRequestError("Provide at least one phase to update.")
    for phase, settings in changes.items():
        if settings is None:
            continue
        if settings.model is not None:
            ensure_model_allowed(phase, settings.model)
        if settings.reasoning_effort is not None:
            ensure_reasoning_effort_allowed(settings.reasoning_effort)

    lock_preferences()
    rows = {row.phase: row for row in load_preferences()}
    for phase, settings in changes.items():
        _apply(phase, settings, rows)
    ensure_judge_differs_from_interviewer((), rows.values())

    db.session.commit()
    return phase_defaults(rows.values())


def _apply(
    phase: GenerationPhase,
    settings: PhaseSettings | None,
    rows: dict[GenerationPhase, PreferencePhaseSettings],
) -> None:
    """Apply one phase's changes to its row, keeping `rows` and the session in step.
    A phase left with nothing customized has no row, so a row always means a choice."""
    row = rows.get(phase) or PreferencePhaseSettings(phase=phase)
    customized = False
    if settings is not None:
        for name in settings.model_fields_set:
            setattr(row, name, getattr(settings, name))
        customized = any(
            getattr(row, name) is not None for name in PhaseSettings.model_fields
        )
    if customized:
        rows[phase] = row
        db.session.add(row)
    else:
        rows.pop(phase, None)
        if inspect(row).persistent:
            db.session.delete(row)
