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

## Documentation

The full design lives in [`docs/`](docs/):

- [`docs/overview.md`](docs/overview.md) — what the app is, pages, known limitations; start here
- [`docs/workflow.md`](docs/workflow.md) — the end-to-end candidate flow
- [`docs/domain-model.md`](docs/domain-model.md) — entities and their fields/relationships
- [`docs/architecture.md`](docs/architecture.md) — technical design, the LLM phases, stack
- [`docs/database-schema.md`](docs/database-schema.md) — concrete Postgres schema
- [`docs/api-design.md`](docs/api-design.md) — the REST contract between client and server
- [`docs/deployment.md`](docs/deployment.md) — how it's containerized and run
- [`docs/spec.md`](docs/spec.md) — the whole design as user stories, ready to slice into issues
- [`CONTEXT.md`](CONTEXT.md) — canonical project vocabulary
- [`docs/adr/`](docs/adr/) — why the hard-to-reverse/non-obvious decisions were made

## Running it

Via Docker Compose (see [`docs/deployment.md`](docs/deployment.md) for what it runs):

```bash
cp interview-practice.server/.env.dev interview-practice.server/.env  # first time only
export OPENROUTER_API_KEY=...  # from wherever it already lives on your machine — never a file in this repo
docker compose up
```

`.env.dev` already has safe local defaults for everything else.

Or run each half manually — see [`interview-practice.client/README.md`](interview-practice.client/README.md)
and [`interview-practice.server/README.md`](interview-practice.server/README.md).
