# Interview Practice — Server

Flask backend, managed with `uv`. Owns every OpenRouter call and the security guard — the
API key and all prompt construction stay server-side; the Angular client
(`interview-practice.client`) never sees either. Structured as a Flask application
factory (`create_app()`) with one Blueprint per domain area
(`interviews`/`documents`/`applications`/`preferences`) — see
[`../docs/api-design.md`](../docs/api-design.md) for the full REST contract.

Early-stage: the Flask app factory and the SQLAlchemy models (`app/models/`) exist, but there
are no routes or tests yet. `pydantic` isn't installed yet — see
[`../docs/database-schema.md`](../docs/database-schema.md) and
[`../docs/architecture.md`](../docs/architecture.md) for what's planned.

For AI-agent-specific conventions (hooks, lint-on-save), see [`CLAUDE.md`](./CLAUDE.md)
rather than this file.

## Commands

```bash
uv sync                                # install dependencies (incl. dev group: mypy, ruff)
uv run flask --app app.app run         # dev server, http://127.0.0.1:5000
uv run flask --app app.app run --debug # dev server with auto-reload/debugger
uv run ruff check .                    # lint
uv run ruff format .                   # format
uv run mypy app                        # type check (strict mode)
uv run pytest                          # run tests (none exist yet)
uv add <package>                       # add a runtime dependency
uv add --dev <package>                 # add a dev dependency
```

### Database migrations

Needs Postgres running (`docker compose up -d db` from the repo root) and a `.env`
(see Configuration below). Run these through the script, not `flask db` directly:

```bash
scripts/db.sh migrate "describe the change"  # generate a migration (review it, then upgrade)
scripts/db.sh upgrade                        # apply pending migrations
scripts/db.sh downgrade                      # undo the latest migration
scripts/db.sh current                        # which revision is the database at?
scripts/db.sh history                        # list all migrations
```

Run `scripts/db.sh upgrade` after the first `docker compose up -d db` and after pulling
anyone's new migrations. The full workflow and caveats are in
[`../docs/database-schema.md`](../docs/database-schema.md#migrations).

## Configuration

```bash
cp .env.dev .env   # first time only
```

`.env.dev` is a checked-in *template*; `.env` is your real, git-ignored local file —
Compose and Flask both read `.env`, never `.env.dev` directly. It has:

| Variable | Used for |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` | assembled into `SQLALCHEMY_DATABASE_URI` at runtime — discrete pieces, not one pre-built URI, so the same values also work as-is for Docker Compose's `db` service (see `../docs/deployment.md`) |
| `CLIENT_HOST`, `CLIENT_PORT` | `flask-cors`'s allowed origin, built as `http://CLIENT_HOST:CLIENT_PORT` — `http://localhost:8002` for local dev (`ng serve` and `flask run` are different origins); a no-op inside Docker Compose, where the browser only ever talks to nginx's single origin |
| `MAX_UPLOAD_MB` | largest document upload in MB (default `10`), the whole request including form fields; the client container's nginx gets the same value (`client_max_body_size`), so change it for both via Compose — see `../docs/deployment.md` |
| `OPENROUTER_BASE_URL` | defaults to the real `https://openrouter.ai/api/v1`; override only to point at another OpenRouter-compatible endpoint (see `../docs/deployment.md`) |

`OPENROUTER_API_KEY` is the one exception — deliberately **not** in `.env.dev`/`.env` or
any other file in this repo. It comes only from wherever it already lives on your own
machine (shell environment). Docker Compose passes it in as a secret, mounted at
`/run/secrets/openrouter_api_key` and referenced by `OPENROUTER_API_KEY_FILE`, so the app
must read the file at that path. Every OpenRouter call (JD/CV analysis, persona/question-plan
generation, live conversation, ask-back suggestions, STAR evaluation, Interviewer
Performance Review, persona image generation) needs it.

`config.py` has a `SECRET_KEY` placeholder that isn't actually wired to anything yet — not
a real configuration requirement right now, so it isn't listed above.

`OPENROUTER_API_KEY`/`OPENROUTER_BASE_URL` aren't wired up yet.

## Where things are documented

This README is just how to run it. What it *does* and why lives in
[`../docs/`](../docs/) — start with [`../docs/overview.md`](../docs/overview.md).
