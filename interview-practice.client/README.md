# Interview Practice — Client

Angular 22 SPA, standalone components, zoneless. The candidate-facing half of the
[Interview Practice](../README.md) app — talks only to the Flask API
(`interview-practice.server`), never calls OpenRouter directly.

UI components via [Spartan](https://spartan.ng) (+ Tailwind CSS); request/response shapes
validated with Zod. See [`../docs/architecture.md`](../docs/architecture.md) for the full
stack rationale, and [`../docs/adr/`](../docs/adr/) for why (e.g.
[ADR 0010](../docs/adr/0010-spartan-for-ui-components.md) for the Spartan choice).

For the whole app (what it is, how to run it end to end, what to know before using it) see
the [root README](../README.md). This file is the client's own setup and commands.

For AI-agent-specific conventions (file naming, hooks), see [`CLAUDE.md`](./CLAUDE.md)
rather than this file.

## Prerequisites

- **Node.js** `^22.22.3`, `^24.15.0` or `>=26.0.0` (Angular 22's requirement), with npm.
  The Docker image builds with Node 22.
- **The server running on `http://localhost:8001`**, with the database up. The dev build
  calls `http://localhost:8001/api`, and the app has nothing to show without it. See [`../interview-practice.server/README.md`](../interview-practice.server/README.md).
- A **Chromium browser** (Chrome or Edge) for the full experience. Reading questions aloud
  and dictating answers use the browser's Web Speech API: dictation works in Chrome and Edge,
  partly in Safari and not in Firefox, and the browser may send the audio to its own speech
  service. Everything else works in any modern browser.

## Run it

```bash
npm install
npm start    # ng serve, dev config, http://localhost:${CLIENT_PORT:-8002}
```

Open <http://localhost:8002>. The port comes from `CLIENT_PORT` in your shell, `8002` if
unset. The server allows exactly that origin through CORS, so if you change it, change
`CLIENT_PORT` for the server too.

Or run the whole app, client included, in Docker from the repo root: see the
[root README](../README.md#quick-start-docker).

## Commands

```bash
npm install
npm start                                   # ng serve, dev config, http://localhost:${CLIENT_PORT:-8002}
npm run build                               # production build to dist/interview-practice.client/browser
npm run watch                               # dev build in watch mode
npm run lint                                # ng lint (eslint over .ts and .html)
npm run format                              # prettier --write .
npm run format:check                        # prettier --check . (no writes)
```

**There are no client tests**, on purpose (see the testing notes in
[`../docs/spec.md`](../docs/spec.md)), and no e2e framework.

## Configuration

The server's base URL lives in `src/environments/environment.ts` (production) and
`environment.development.ts` (`ng serve`) as `environment.apiUrl` — not an OS-level env var,
since this ships as a static build with no `process.env` at runtime in the browser:

| Build                                                  | `apiUrl`                    | Why                                                                                |
| ------------------------------------------------------ | --------------------------- | ---------------------------------------------------------------------------------- |
| `npm start` (development)                              | `http://localhost:8001/api` | a different origin from `ng serve`, so real cross-origin CORS                      |
| `npm run build` (production, used by the Docker image) | `/api`                      | same origin: nginx serves the build and proxies `/api/*` to the server, so no CORS |

See [`../docs/architecture.md`](../docs/architecture.md) and [`../docs/deployment.md`](../docs/deployment.md).

## Code layout

```
src/app/
  app.routes.ts       the routes (lazy-loaded pages)
  core/               app-wide pieces: API error handling, leave-confirmation guard,
                      layout (topbar, breadcrumbs), per-phase model settings and the judge
                      rule, speech (read aloud, dictation, mic meter), theme
  features/           one folder per area:
    home/             the dashboard
    interviews/       create interview, the live session, results
    applications/     the application overview and progress summary
    history/          the history sidebar
    documents/        document API and models
    preferences/      model defaults and the document library
  shared/components/  small reusable components; ui/ holds the generated Spartan components
```

Imports that would climb two or more levels use the aliases `@app/*` (`src/app/*`) and
`@env/*` (`src/environments/*`).

## Things worth knowing

- **Dark mode is the default**; the toggle in the top bar is remembered in the browser.
- **Reading questions aloud is off by default** (toggle in the session header).
- **The app asks before you leave** Create Interview, the live session and Preferences (when
  there are unsaved model defaults); on the first two it also warns when you close the tab.
- **The history sidebar** is shown on Home, Results, Preferences and the application page, and
  hidden during Create and the live session. Its width is remembered.
- After running Spartan's generator, restart `ng serve`: the `tsconfig` alias change leaves
  a running dev server stale.

## Where things are documented

This README is just how to run it. What it _does_ and why lives in
[`../docs/`](../docs/) — start with [`../docs/overview.md`](../docs/overview.md).
