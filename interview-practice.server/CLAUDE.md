# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Flask backend for the `interview-practice` repo, managed with `uv`. Early stage: an application factory and the SQLAlchemy models exist, but there are no routes or tests yet. See `../CLAUDE.md` for the repo layout.

## Commands

```bash
uv sync                                # install dependencies (incl. dev group: mypy, ruff)
uv run flask --app app.app run         # dev server, http://127.0.0.1:5000
uv run flask --app app.app run --debug # dev server with auto-reload/debugger
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run mypy app                        # type check (strict mode)
uv run pytest                          # run tests (no tests exist yet)
scripts/db.sh migrate "message"        # generate a migration (review it, then upgrade)
scripts/db.sh upgrade                  # apply pending migrations (also: downgrade, current, history)
uv add <package>                       # add a runtime dependency
uv add --dev <package>                 # add a dev dependency
```

There is no `tests/` directory yet; `[tool.ruff.lint.per-file-ignores]` and `[tool.mypy] exclude` in `pyproject.toml` already anticipate one.

## Architecture and conventions

- Entry point is `app/app.py`, which defines the `create_app()` factory (there is no module-level `app` instance). Reference it as `app.app` (module path) when invoking `flask` commands — Flask finds `create_app` automatically — and as `'app.app:create_app()'` for gunicorn, not the bare filename. CORS builds its allowed origin as `http://CLIENT_HOST:CLIENT_PORT` (defaults `localhost` and `8002`), not hardcoded.
- `config.py` at the repo root defines a `Config` class read from environment variables via `python-dotenv`'s `load_dotenv()`: `SQLALCHEMY_DATABASE_URI`, assembled from the discrete `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_HOST`/`POSTGRES_PORT`/`POSTGRES_DB` variables (there is no pre-built `DATABASE_URL`). `flask-sqlalchemy`/`sqlalchemy`/`flask-migrate` are installed and the models live in `app/models/` (register new ones in `app/models/__init__.py`); `pydantic` is not yet. Run migrations through `scripts/db.sh` (see `../docs/database-schema.md#migrations`), not `flask db` directly. `config.py` has no `SECRET_KEY` and nothing uses one yet. `gunicorn` *is* already a dependency (for the Docker image, see below). `.env.dev` is a checked-in template; copy it to `.env` (git-ignored) for real local values — see `../docs/deployment.md`.
- Domain Blueprints live in `app/<domain>/` (`routes.py`, `schemas.py` with Pydantic models, plus helpers). `app/interviews/` and `app/documents/` also have `use_cases/`, one module per endpoint holding the whole logic (loading, rules, LLM calls, storing, committing) and returning domain objects; their `routes.py` is only the HTTP layer (parse the request, call a use case, build the response). A use case that grows private helpers becomes a package (`use_cases/create_interview/`, same import path) with those helpers next to it; code used by several use cases lives in the domain's `shared/` folder, and slices never import each other. `app/services/` holds capabilities shared across domains (e.g. `document_analysis`, used by both documents and interviews; `interview_lifecycle`, used by interviews and applications); services depend only on `models`, `llm` and `errors`, never on a domain, so the domains have no import cycles and are registered in `create_app()`; `app/documents/` is the first, then `app/applications/` (list only so far). `app/errors/` implements the API error contract, split in two: `exceptions.py` has the `ApiError` subclasses to raise from routes (`BadRequestError` 400, `NotFoundError` 404, `ConflictError` 409, `FileTooLargeError` 413, `UnprocessableFileError` 422 — each fixes its HTTP status and a default code, so you pass only a message, plus `code=` for a more specific one like `ConflictError("...", code="INTERVIEW_ALREADY_ENDED")`), and `handlers.py` registers the Flask error handlers that turn them into the JSON error shape. Don't build error responses by hand. For a new status, add a small subclass in `exceptions.py` and a matching row in `docs/api-design.md`'s error table. Responses go through the DTOs in each domain's `schemas.py` (e.g. `DocumentPublic`) via `to_json` / `to_json_list` in `app/serialization.py` — never return ORM objects directly. Uploads are stored under the Flask `instance/` folder (git-ignored; get it with `instance_dir()` from `app/paths.py`), with `Document.file_path` relative to it.
- `static/` and `templates/` exist but are empty, following default Flask conventions for static assets and Jinja templates.
- `create_app()` is built; the Blueprints (one per domain area) are not yet. Extensions (`db`, `migrate`) live in `app/extensions.py`, models in `app/models/`. See `../docs/architecture.md` and `../docs/api-design.md` before adding routes, so each domain area gets its own Blueprint, registered in `create_app()`, rather than growing `app.py` monolithically.
- `Dockerfile`/`.dockerignore` exist for the Docker Compose deployment — see `../docs/deployment.md`.
- Ruff (`[tool.ruff]`, `[tool.ruff.lint]` in `pyproject.toml`): target `py312`, line length 88, rule set `E, W, F, I, B, C90, UP, SIM, RUF`.
- Mypy (`[tool.mypy]`): `strict = true`, `disallow_untyped_defs = true`, `warn_return_any = true` — new functions need full type annotations. `migrations` and `tests` are excluded.
- `.editorconfig`: 4-space indent, UTF-8, final newline, trimmed trailing whitespace; Python lines capped at 88 (matches Ruff), Markdown line length unrestricted.

## Claude Code hooks (`.claude/settings.json`)

- After editing/writing any `.py` file, a `PostToolUse` hook runs `uv run ruff format` on it automatically.
- On `Stop`, a hook runs `uv run ruff check . && uv run mypy app` — fix lint/type errors it reports before finishing a task.
- Allowed without prompting: `ruff`, `mypy`, `pytest`, `flask db *`, `flask run *`, `uv add/sync/run`, and read-only file tools. `git commit`/`git push` and reading `.env` are denied (consistent with the repo-wide git operations policy in `../CLAUDE.md`).
