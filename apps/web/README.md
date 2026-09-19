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
npm test        # Vitest + React Testing Library, jsdom
npm run e2e     # Playwright, real browser + real stack -- local only, see e2e/README.md
npm run lint
npm run build   # also typechecks (tests included)
```

`npm test` runs 60 tests covering `lib/api.ts` (error mapping, the 15s timeout, multipart encoding), the shared components, and the behavior of every page (landing, login, register, upload, processing, pick, results). They mock `@/lib/api` and `next/navigation`, so they prove each page does the right thing *given* a response -- not that the real API returns that shape. Mutation-checked: deliberately breaking the gauge's clamping, the client timeout, and the processing page's redirect-once guard each turned exactly one test red. jsdom is not a browser, so a separate Playwright suite (`e2e/`, local only, not in CI) drives real Edge against the real API, queue and worker -- including attaching real videos to the actual file inputs. There are no visual-regression tests.

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
- **The native OS file-picker *dialog* still hasn't been clicked through** -- no tooling here can drive it. But Playwright's `setInputFiles` drives the real `<input type="file">` that dialog would fill, so the form, `Dropzone`, the multipart upload, the worker and the results page have now been exercised in a real browser with the real clips (`e2e/analysis.spec.ts`: score 38.6, matching the direct runs).
- Test gaps: the unit/page tests mock the API client, so frontend/backend contract drift is caught only by the shared `@cadence/schema` types and the e2e suite. The e2e suite is local-only (needs Redis, a worker with ML dependencies, ffmpeg and real videos, so it can't run in CI) and drives Edge only. It now covers the happy path, auth, the dancer-pick flow, a no-person video being rejected, a non-YouTube link being refused, and an automated no-sideways-scroll check at 390/768/1440px -- and a rejected *reference* video, but not the YouTube-link *happy path* (it would download a real video) or other browsers. No visual-regression tests.
- Responsive layout is mobile-first (`md` = 768px is where it becomes the desktop layout). It was checked by eye at 390px and 1440px, and the e2e suite now asserts *no sideways scroll* at 390, 768 and 1440px on landing, login, register, upload, pick and results -- an automated check for overflow, not for whether it looks good at tablet width, and not run on a real device. The video areas are still empty placeholders (there's no real video URL to play yet), so how they behave with real footage on a phone is unverified.
- CORS in `apps/api/app/main.py` hardcodes `http://localhost:3000` as the only allowed origin -- fine for local dev, needs a real origin (and probably an env var) before this points at anything deployed.
