# Interview Practice — Server

Flask backend, managed with `uv`. Owns every OpenRouter call and the security guard — the
API key and all prompt construction stay server-side; the Angular client
(`interview-practice.client`) never sees either. Structured as a Flask application
factory (`create_app()`) with one Blueprint per domain area
(`interviews`/`documents`/`applications`/`preferences`/`dashboard`) — see
[`../docs/api-design.md`](../docs/api-design.md) for the full REST contract.

For the whole app (what it is, how to run it end to end, what to know before using it) see
the [root README](../README.md). This file is the server's own setup and commands.

For AI-agent-specific conventions (hooks, lint-on-save), see [`CLAUDE.md`](./CLAUDE.md)
rather than this file.

## Prerequisites

- **Python 3.12+** and [**uv**](https://docs.astral.sh/uv/). `uv sync` installs the
  dependencies (and a matching Python if needed).
- **Postgres 16**, reachable at `POSTGRES_HOST:POSTGRES_PORT`. The easiest way is the
  Compose `db` service, which needs Docker and the `.env` file below.
- A **`.env` file** (see Configuration). The server will not start without the `POSTGRES_*`
  values.
- An **OpenRouter API key** in your shell as `OPENROUTER_API_KEY`, for anything that calls
  a model. The app boots without it, but those calls fail with a `503`.

## Run it

From this folder (`interview-practice.server`):

```bash
cp .env.dev .env                                   # first time only
docker compose -f ../docker-compose.yml up -d db   # Postgres (or any Postgres you already run)
export OPENROUTER_API_KEY=...                      # from your own machine, never a file in the repo
uv sync                                            # install dependencies
scripts/db.sh upgrade                              # create/update the schema
uv run flask --app app.app run --port 8001 --debug
```

The API is then at `http://localhost:8001/api`. **Use port 8001**: it's what the client's
dev config calls (`flask run` alone would pick 5000). The CORS allowed origin is
`http://CLIENT_HOST:CLIENT_PORT`, `http://localhost:8002` by default, which is where
`npm start` serves the client.

Inside Docker the image runs `flask db upgrade` and then gunicorn on every start, so the
container needs no manual migration step (see [`../docs/deployment.md`](../docs/deployment.md)).

## Commands

```bash
uv sync                                              # install dependencies (incl. dev group: mypy, ruff, pytest)
uv run flask --app app.app run --port 8001           # dev server
uv run flask --app app.app run --port 8001 --debug   # dev server with auto-reload/debugger
uv run ruff check .                                  # lint
uv run ruff format .                                 # format
uv run mypy app                                      # type check (strict mode)
uv run pytest                                        # run tests
uv add <package>                                     # add a runtime dependency
uv add --dev <package>                               # add a dev dependency
```

### Tests

`uv run pytest` runs the server's tests. They need **no database and no network**: models
are built unsaved and the OpenRouter client talks to a fake transport (`tests/support.py`
has the shared helpers). They cover the critical parts: the security guard, the OpenRouter
client, exchange pacing, planning, the lifecycle and staleness rules, results, phase
settings, preferences, concurrency and the application progress summary. Coverage is
partial: document upload and PDF parsing, and the HTTP routes, aren't tested.

### Database migrations

Needs Postgres running and a `.env`. Run these through the script, not `flask db` directly,
because it loads `.env`, checks the variables and that the database is reachable:

```bash
scripts/db.sh migrate "describe the change"  # generate a migration (review it, then upgrade)
scripts/db.sh upgrade                        # apply pending migrations
scripts/db.sh downgrade                      # undo the latest migration
scripts/db.sh current                        # which revision is the database at?
scripts/db.sh history                        # list all migrations
```

Run `scripts/db.sh upgrade` after the first `docker compose up -d db` and after pulling
anyone's new migrations. Schema changes are new migrations; don't edit one that has been
committed. The full workflow and caveats are in
[`../docs/database-schema.md`](../docs/database-schema.md#migrations).

## Configuration

`.env.dev` is a checked-in *template*; `.env` is your real, git-ignored local file —
Compose and Flask both read `.env`, never `.env.dev` directly. It has:

| Variable | Used for |
|---|---|
| `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`, `POSTGRES_PORT` | assembled into `SQLALCHEMY_DATABASE_URI` at runtime — discrete pieces, not one pre-built URI, so the same values also work as-is for Docker Compose's `db` service (see `../docs/deployment.md`). Required. |
| `CLIENT_HOST`, `CLIENT_PORT` | `flask-cors`'s allowed origin, built as `http://CLIENT_HOST:CLIENT_PORT` — `http://localhost:8002` for local dev (`ng serve` and `flask run` are different origins); a no-op inside Docker Compose, where the browser only ever talks to nginx's single origin |
| `SERVER_PORT` | the port Docker Compose and the container use (`8001`). `flask run` ignores it: pass `--port 8001` yourself |
| `MAX_UPLOAD_MB` | largest document upload in MB (default `10`), the whole request including form fields; the client container's nginx gets the same value (`client_max_body_size`), so change it for both via Compose — see `../docs/deployment.md` |
| `OPENROUTER_BASE_URL` | defaults to the real `https://openrouter.ai/api/v1`; override only to point at another OpenRouter-compatible endpoint |
| `LLM_TIMEOUT_SECONDS` | how long one OpenRouter chat call may take (default `60`); a longer one is a `504 LLM_TIMEOUT`. Portrait generation has its own fixed 120 s limit |
| `PORTRAIT_GENERATION_ENABLED` | default `true`. `false` skips the persona portrait, which is slow and billed; interviews are then created without one |

`OPENROUTER_API_KEY` is the one exception — deliberately **not** in `.env.dev`/`.env` or
any other file in this repo. It comes only from wherever it already lives on your own
machine (shell environment). Outside Docker the server reads the plain `OPENROUTER_API_KEY`
variable. Docker Compose passes it in as a secret, mounted at
`/run/secrets/openrouter_api_key` and referenced by `OPENROUTER_API_KEY_FILE`; when that
variable is set the server reads the file instead, on every call, so a rotated key needs no
restart. Every OpenRouter call (JD/CV analysis, persona/question-plan/criteria generation,
live conversation, coaching hints, ask-back suggestions, STAR evaluation, interviewer review,
progress summary, persona image generation) needs it.

## Code layout

```
app/
  app.py                  create_app(): config, CORS, blueprints, error handlers
  interviews/ documents/ applications/ preferences/ dashboard/
                          one Blueprint each: routes.py (HTTP only), schemas.py (Pydantic),
                          use_cases/ (one module or package per endpoint), shared/
  llm/                    OpenRouter client, the security guard (guard.py), per-phase
                          model settings (phase_settings.py), step timing
  services/               capabilities shared across domains (document analysis,
                          interview lifecycle/staleness, portrait files, preferences)
  models/                 SQLAlchemy models, one file per table
  errors/                 the API error contract (exceptions.py, handlers.py)
migrations/               Alembic/Flask-Migrate versions
scripts/db.sh             migration wrapper
tests/                    DB-free unit tests
instance/uploads/         uploaded documents and generated portraits (git-ignored, a Docker volume in deployment)
```

## Things worth knowing

- **Every model call is billed** to your OpenRouter account, and the document text and the
  candidate's answers are sent to OpenRouter and the model providers behind it.
- **The security guard** (`app/llm/guard.py`) checks the texts that come from the candidate
  (uploaded documents, free-text fields, chat messages): length limits, prompt-injection
  rules and the provider's moderation. A rejected text is a
  `422 INPUT_REJECTED` and nothing is stored.
- **Sessions are closed lazily.** There is no background job: an interview with no activity
  for 30 minutes is marked abandoned the next time it is read (ADR 0006).
- **Some failures are deliberately quiet.** If the interviewer-review judge fails, the
  evaluation is still saved without it, and a failed portrait leaves a fallback avatar.
  The reason is in the server log.
- **Uploaded files** are stored under `instance/uploads/`, which is git-ignored.

## Where things are documented

This README is just how to run it. What it *does* and why lives in
[`../docs/`](../docs/) — start with [`../docs/overview.md`](../docs/overview.md).
