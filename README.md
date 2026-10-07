# Interview Practice

A mock-interview practice app: describe the role you're preparing for, run a simulated
multi-turn interview against an AI interviewer shaped by that role and your own
documents, and get back a structured, STAR-based evaluation — closer to rehearsing a real
interview than a one-shot question generator.

Built as a course project (prompt engineering, LLM settings, and a security guard, behind
a real front end — see [`docs/adr/0001-flask-and-angular-over-streamlit-or-nextjs.md`](docs/adr/0001-flask-and-angular-over-streamlit-or-nextjs.md)
for why this is Flask + Angular rather than the suggested Streamlit/Next.js).

## Repository layout

- [`interview-practice.client/`](interview-practice.client/) — Angular 22 SPA. See its own
  [README](interview-practice.client/README.md) for client-specific dev commands.
- [`interview-practice.server/`](interview-practice.server/) — Flask backend. See its own
  [README](interview-practice.server/README.md) for server-specific dev commands.
- [`docs/`](docs/) — the design: product, data model, API, architecture, decisions.
- `docker-compose.yml` — runs the whole app (client, server, database).

## What you need

| You need | Why |
|---|---|
| **An OpenRouter API key**, with credit | Every AI feature goes through [OpenRouter](https://openrouter.ai). Without a key the app starts, but anything that calls a model fails (the server answers `503`, "the AI service is not available"). The default models are `gpt-5-mini` (interviewer, evaluation), `google/gemini-2.5-flash` (the interviewer review) and `google/gemini-2.5-flash-image` (persona portraits), so the key must be allowed to use them. |
| **Docker** with Compose v2 | Runs everything for the quick start, and the Postgres database in both modes. |
| *Development without Docker for the app only:* **Node.js** `^22.22.3`, `^24.15` or `>=26` (with npm) | Required by Angular 22. |
| *Same:* **Python** 3.12+ and [**uv**](https://docs.astral.sh/uv/) | The server's package manager; `uv` installs the dependencies and the right Python for you. |
| A **Chromium browser** (Chrome or Edge) | The app works in any modern browser, but reading questions aloud and dictating answers use the browser's speech features. Dictation works in Chrome and Edge, partly in Safari and not in Firefox (see [Things worth knowing](#things-worth-knowing)). |

The key is read only from your own machine's environment and is never written to a file in
this repo.

## Quick start (Docker)

```bash
cp interview-practice.server/.env.dev interview-practice.server/.env   # first time only
export OPENROUTER_API_KEY=...   # from wherever the key already lives on your machine
docker compose up --build
```

Then open **<http://localhost:8002>**.

- The first run builds the images, so it takes a few minutes.
- The `server` container applies the database migrations by itself on every start, after
  the database reports healthy. There is nothing else to set up.
- Ports: client `8002`, server API `8001`, Postgres `5432` (bound to `127.0.0.1` only).
  Export `CLIENT_PORT` or `SERVER_PORT` before `docker compose up` to change the first two.
- Your data lives in two Docker volumes (the database and the uploaded files and portraits),
  so it survives restarts. `docker compose down -v` **deletes both**, which is also how you
  start over from empty.

## Run it for development (hot reload)

Run the database in Docker and the server and client on your machine. Use three terminals,
from the repo root.

```bash
# 1. Database
cp interview-practice.server/.env.dev interview-practice.server/.env   # first time only
docker compose up -d db

# 2. Server, on port 8001 (the client's dev config calls that port)
cd interview-practice.server
export OPENROUTER_API_KEY=...
scripts/db.sh upgrade                                # first time, and after pulling new migrations
uv run flask --app app.app run --port 8001 --debug

# 3. Client, on port 8002
cd interview-practice.client
npm install
npm start
```

Open **<http://localhost:8002>**. The client and server are on different origins here, so
the server allows `http://localhost:8002` through CORS (set by `CLIENT_HOST` and
`CLIENT_PORT`). Keep the server on `8001` and the client on `8002`, or change both sides.

More commands (lint, format, tests, migrations) are in the two READMEs below.

## Try it

1. On the Home page choose **+ New interview**.
2. Fill in a job title and seniority, pick a difficulty and who interviews you (recruiter,
   technical screener, HR or hiring manager). The interviewer's role seeds the tone and the
   interview type, and you can change both.
3. Optionally upload a job description, CV or cover letter (PDF) and turn on coaching hints.
4. **Create.** This makes several model calls, so expect a short wait; a progress screen shows
   what it's doing.
5. Answer the interviewer's questions in the chat, then use the ask-back phase to ask your own.
   You can abandon at any point and still get feedback on what you said.
6. The **Results** page produces the STAR evaluation, a hire / no-hire verdict and what to work
   on, plus a separate, developer-facing review of the interviewer's own conduct.
7. Link several interviews to one job application (for example a recruiter screen, then a
   technical round) to see a progress summary across the stages.

Model, temperature, token and reasoning settings per phase are in **Preferences**, and you can
override them for a single interview under *Phase-Specific Model Overrides* in Create.

## Things worth knowing

- **It costs money.** Every model call is billed to your OpenRouter account: reading the
  documents, planning the interview, every reply, the evaluation, the review, and the
  generated portrait of the interviewer. The portrait is the slow and billed extra; set
  `PORTRAIT_GENERATION_ENABLED=false` in `interview-practice.server/.env` to skip it.
- **Your text leaves your machine.** The documents you upload and your answers are sent to
  OpenRouter and the model providers behind it. Don't upload anything you wouldn't send to
  them.
- **Documents are PDF only**, at most 10 MB (`MAX_UPLOAD_MB`), and must contain real text:
  scanned or encrypted PDFs are refused. The original file is kept so you can download it again.
- **Single user, no login.** Everything in the database belongs to whoever opens the app. See
  [ADR 0002](docs/adr/0002-single-user-prototype-no-auth.md).
- **Voice is browser-side.** Reading questions aloud is off by default (a toggle in the session
  header). Dictation uses the browser's own speech recognition, which in Chrome and Edge
  usually sends the audio to the browser vendor's servers, and the browser asks for microphone
  permission.
- **Interviews can end early.** If you are rude or abusive the interviewer warns you first and
  then ends the interview, and the evaluation takes that into account. A session left idle
  for 30 minutes is closed as abandoned the next time it is read.
- **Known limitations** (no renaming of history entries, no one-click "add stage" in the
  sidebar, partial test coverage, no logging strategy) are listed in
  [`docs/overview.md`](docs/overview.md#known-limitations).

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `KeyError: 'POSTGRES_USER'` when starting the server | There is no `interview-practice.server/.env`. Copy `.env.dev` to `.env`. |
| Errors about missing tables or relations | Migrations haven't been applied. Run `scripts/db.sh upgrade` (the Docker server does this for you). |
| Model calls fail with "The AI service is not available right now" | `OPENROUTER_API_KEY` isn't set in the shell that started the server, or OpenRouter is rejecting the key or the credit. The server log has OpenRouter's own message. |
| A CORS error in the browser console during development | The server isn't running on port `8001`, or the client isn't on `8002`. |
| The `server` container exits on start | Run `docker compose logs server`. A failed migration, for example against a database left by an older schema, stops it on purpose. `docker compose down -v` starts clean, and deletes your data. |
| No portrait for the interviewer | Portrait generation is switched off, or the image call failed. The interview works without it. |
| The interviewer review is missing on the Results page | The review is optional: if the judge model fails the evaluation is still saved. The server log has the reason. |

## Documentation

The full design lives in [`docs/`](docs/):

- [`docs/overview.md`](docs/overview.md) — what the app is, pages, known limitations; start here
- [`docs/workflow.md`](docs/workflow.md) — the end-to-end candidate flow
- [`docs/domain-model.md`](docs/domain-model.md) — entities and their fields/relationships
- [`docs/architecture.md`](docs/architecture.md) — technical design, the LLM phases, stack
- [`docs/prompt-engineering.md`](docs/prompt-engineering.md) — every prompt: technique, rules, output contract, settings, how they were iterated
- [`docs/database-schema.md`](docs/database-schema.md) — concrete Postgres schema
- [`docs/api-design.md`](docs/api-design.md) — the REST contract between client and server
- [`docs/deployment.md`](docs/deployment.md) — how it's containerized and run
- [`docs/spec.md`](docs/spec.md) — the whole design as user stories, ready to slice into issues
- [`CONTEXT.md`](CONTEXT.md) — canonical project vocabulary
- [`docs/adr/`](docs/adr/) — why the hard-to-reverse/non-obvious decisions were made
