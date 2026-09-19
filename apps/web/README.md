# apps/web — Cadence Arena UI

Next.js 16 (App Router) + TypeScript + Tailwind v4. Scaffolded with `create-next-app`, now a real client wired to `apps/api`.

## Run locally

Needs `apps/api` running on port 8000 (`uvicorn app.main:app --reload --port 8000` from `apps/api`, with a venv that has its requirements installed) -- every page here calls the real API, there's no mock data layer.

```bash
cp .env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to http://localhost:8000 if you skip this
npm install
npm run dev
```

Open http://localhost:3000.

## Test / lint

```bash
npm run lint
npm run build   # also typechecks
```

No component/integration tests yet (see "What's not real yet" below) -- `npm run build` is the only automated check today, and it only catches type errors, not behavior.

## What's here

- **`lib/api.ts`** -- the only place that talks to `apps/api`. Every call sends `credentials: "include"` (auth is a cookie the browser holds, not a bearer token this app manages) and times out after 15s via `AbortController`, so a hung backend call (see the Redis caveat below) surfaces as an error instead of an infinite spinner.
- **`lib/issueTypes.tsx`** -- the single place mapping `IssueType` (from `@cadence/schema`) to a color/icon/caption. Both the Results page's real timeline and its "no issues yet" explainer read from this, so the two can't drift.
- **`@cadence/schema`** is now actually wired in -- via a `file:` dependency in `package.json` (not npm workspaces, despite what an earlier version of this file said; a full root-level workspace would also change how CI installs `apps/web` and `packages/schema/typescript`, which wasn't needed just to import types) plus `transpilePackages` in `next.config.ts`, since the package ships raw `.ts` source with no build step.
- **Pages**: `/` (marketing landing), `/login`, `/register`, `/studio/upload` (auth-gated, checks `/auth/me` on mount), `/studio/processing/[id]` (polls `GET /analyses/{id}` every 2.5s and routes to pick/results/upload based on `status`), `/studio/pick/[id]`, `/studio/results/[id]`. Each dynamic page is a thin async server component that awaits `params` and hands the plain `id` to a `"use client"` component that does the actual fetching -- client components can't be `async`, and every real API call needs the browser's cookie jar anyway.
- Visual language ported from the Claude Design canvas built earlier this session (lavender/blue palette, italic Fraunces wordmark, icon-badge infographics, no literal gradients) -- see `components/` for the shared pieces (`Logo`, `Button`, `IconBadge`, `ScoreGauge`, `VideoToggle`, `Toast`).

## What's real vs. not yet

**Real:** register/login/logout against `apps/api`'s actual cookie-session auth, the multipart upload to `POST /analyses`, polling a real `AnalysisResult`, the dancer-pick flow against real candidate-track data, and the Results page's score/stats/timeline -- all built from the actual response shape in `@cadence/schema`, with `null`/zero values rendered as "--" rather than invented numbers.

**Not yet:**
- **Real Redis and Postgres still haven't been used** (no Docker here). The full path -- upload -> API -> queue -> real worker -> scored result -> this UI's processing page polling and auto-redirecting to Results -- *has* been verified end to end on the two real dance clips, but against a pure-Python fake Redis (`apps/worker/scripts/dev_fake_redis.py`) and SQLite. That retires "is the wiring right," not "does it behave on real infrastructure." One trap found along the way: `REDIS_URL` must say `127.0.0.1`, not `localhost`, on Windows (IPv6-first resolution hangs). Before that was set up, `POST /analyses` and `POST /analyses/{id}/lock` blocked forever on `arq.create_pool` trying to reach Redis -- hence the client-side timeout in `lib/api.ts`.
- **File uploads weren't exercised through the real browser file picker** -- this session's browser-automation tools can't drive the native OS file dialog `<input type="file">` opens. The end-to-end run above submitted the same multipart request with `curl`, so the endpoint and everything after it is proven; `Dropzone` itself is verified only by code review and the build/typecheck passing.
- No automated tests (unit or e2e) for any page or component -- everything above was verified by hand, once, in this session. That's a real gap if this keeps growing.
- No responsive/mobile layout -- built and checked at 1440px only, matching the design canvas; narrow viewports will wrap awkwardly (seen directly in this session's own testing).
- CORS in `apps/api/app/main.py` hardcodes `http://localhost:3000` as the only allowed origin -- fine for local dev, needs a real origin (and probably an env var) before this points at anything deployed.
