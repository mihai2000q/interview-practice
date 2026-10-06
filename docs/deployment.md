# Deployment

Docker Compose, single-host — not an orchestrated/multi-instance setup. That scope call
also resolves an open caveat in [`architecture.md`](./architecture.md): local-disk file
storage was flagged as needing revisiting "before any multi-instance deployment" — since
multi-instance isn't the goal here, that revisit isn't needed, as long as the upload/persona
volume (below) actually persists.

**Project name pinned explicitly** (Compose's top-level `name:` key — `interview-practice`),
rather than left to derive from the containing directory. Compose names every container
`<project>-<service>-<n>` (`interview-practice-client-1`, `interview-practice-server-1`,
etc.), so an explicit name keeps them grouped under one recognizable prefix in `docker ps`
regardless of what the repo's folder happens to be called or which directory Compose is
invoked from — relying on the directory-name default would break that grouping silently.

## Services

- **`client`** — Angular, multi-stage Dockerfile: Node build stage producing `dist/`, then
  served from an nginx stage. nginx also reverse-proxies `/api/*` to the `server` service
  by Docker Compose service name, so the browser only ever talks to one origin — sidesteps
  CORS in this deployment shape entirely (local dev outside Docker still needs
  `flask-cors`, already a dependency, for the separate `ng serve`/`flask run` origins).
- **`server`** — Flask, Python 3.12, deps via `uv`. Run through a real WSGI server
  (gunicorn), not `flask run`'s dev server.
- **`db`** — official `postgres` image.
- **`mock-llm`** (local dev only, opt-in) — [MockServer](https://www.mock-server.com/mock_server/llm_response_mocking.html),
  behind a Compose **profile** (e.g. `docker compose --profile mock up`) so it never runs
  as part of the normal stack. Stands in for OpenRouter with canned/configurable
  chat-completion responses — zero cost, deterministic, no GPU or real model needed.
  Useful for exercising the app's own plumbing (does it call and parse responses
  correctly) without real API spend; not a substitute for judging actual output quality.
  Requires the server's OpenRouter base URL to be configurable rather than hardcoded —
  see `OPENROUTER_BASE_URL` below.

## Volumes

- **Postgres data** — named volume, standard.
- **`instance/uploads`** — named volume mounted into the `server` container at its
  `instance/` path. This is the one that actually matters: it's where `Document.file_path`
  and `Interview.persona_image_path` live (see `architecture.md`) — without this volume,
  every uploaded CV/cover letter/job description and every generated persona portrait
  vanishes the moment the container is recreated.

## Configuration

One template, one real file, one exception:

- **`interview-practice.server/.env.dev`** is the checked-in *template* — copy it to
  `.env` to get started (`cp interview-practice.server/.env.dev interview-practice.server/.env`).
  `.env` is the real, git-ignored file Compose and Flask actually read; `.env.dev` itself
  is never read at runtime, it just seeds `.env`'s starting values. Holds everything
  that's safe to keep in a file — nothing secret, just dev-scoped values and config
  defaults:
  - **Database**: `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, `POSTGRES_HOST`,
    `POSTGRES_PORT` — discrete pieces, not one pre-built `DATABASE_URL`. The official
    `postgres` image natively expects `POSTGRES_USER`/`POSTGRES_PASSWORD`/`POSTGRES_DB` to
    initialize itself, so those same values are the single source of truth for both the
    `db` service and the `server` service's connection string — `config.py` needs to
    change from reading a pre-built `SQLALCHEMY_DATABASE_URI` to *assembling* one from
    these pieces at runtime (`postgresql://{user}:{password}@{host}:{port}/{db}`),
    otherwise the same credentials end up typed twice.
  - **`CLIENT_HOST`** / **`CLIENT_PORT`**: the server-side CORS allowed-origin is built
    from these as `http://CLIENT_HOST:CLIENT_PORT` and passed to `flask-cors`; unset, they
    default to `localhost` and `8002`. Only
    actually matters for local dev (`http://localhost:8002`, a different origin from
    a local `flask run --port 8001`, the same `SERVER_PORT` Compose uses) — inside
    Docker Compose, the browser only ever talks to nginx's single origin (see the
    `client` service above), so CORS is a no-op there regardless of what this is set to.
  - **`MAX_UPLOAD_MB`**: largest document upload, in MB (default 10) — the size of the
    whole upload request, so a file just under the limit plus its form fields can still be
    rejected. Two places enforce it and must agree: Flask (`MAX_CONTENT_LENGTH`, with a
    clearer per-file `413 FILE_TOO_LARGE`) and the `client` container's nginx
    (`client_max_body_size`, rendered from the same variable — nginx's own default of 1 MB
    would otherwise reject uploads first). Compose passes the same `${MAX_UPLOAD_MB:-10}` to
    both services, the way it does `CLIENT_PORT`/`SERVER_PORT`.
  - **`OPENROUTER_BASE_URL`**: defaults to the real `https://openrouter.ai/api/v1`;
    override to point at the `mock-llm` service instead when that profile is running.
    Requires the backend's OpenRouter client to read this from config rather than
    hardcoding the real URL — a small, cheap change worth making regardless of whether
    `mock-llm` gets used.
  - **`PORTRAIT_GENERATION_ENABLED`**: defaults to `true`. Set it to `false` (also `0`, `no`,
    `off`) to skip the persona portrait, which is slow and billed: `PUT
    /api/interviews/:id/persona-image` then returns `personaImageUrl: null` without calling
    the model. It reaches
    the `server` container through its `env_file`, like the other `.env` values.
- **`OPENROUTER_API_KEY`** is the one exception — deliberately **not** in `.env.dev`/`.env`
  or any other file in this repo. It stays wherever it already lives on each developer's
  own machine (shell environment). `docker-compose.yml` declares it as a Compose
  **secret** sourced from the host's `OPENROUTER_API_KEY` (`environment:` source), mounted
  into the `server` container at `/run/secrets/openrouter_api_key`; the container gets
  `OPENROUTER_API_KEY_FILE` pointing there and the app reads the key from that file. So it
  never needs to be written to disk inside the project, and it isn't a plain env var in
  the container (doesn't show up in `docker inspect`).

`config.py` also has a `SECRET_KEY` placeholder, but it isn't wired to anything yet — not
a real configuration requirement right now, so it's deliberately not in `.env.dev`/`.env`
either.

## Explicitly out of scope here

- CI/CD pipeline, cloud hosting choice — containerizing the app and running it via Compose
  is the scope of this pass; where it actually *runs* long-term is still open.
- Horizontal scaling / multi-instance — see the local-disk-storage note above.
- Scheduled maintenance, such as cleaning up abandoned document uploads (and object-storage
  lifecycle rules if files ever leave local disk) — see
  [ADR 0011](./adr/0011-documents-are-uploaded-before-the-interview-is-created.md).
