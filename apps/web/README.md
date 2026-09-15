# apps/web — Cadence Arena UI

Next.js 15 + TypeScript + Tailwind. Scaffolded with `create-next-app`.

## Run locally

```bash
npm install
npm run dev
```

Open http://localhost:3000.

## Test / lint

```bash
npm run lint
npm run build   # also typechecks
```

## Roadmap

Currently Phase 0 (placeholder hello page). The real Arena UI — score slam, timeline, 3D skeleton (R3F), Rive HUD — lands in Phase 4, once `apps/api` returns real `AnalysisResult`s. See [`../../ROADMAP.md`](../../ROADMAP.md) and [`../../STATUS.md`](../../STATUS.md).

`@cadence/schema` (the TypeScript `AnalysisResult` types in [`../../packages/schema/typescript`](../../packages/schema/typescript)) gets wired in via npm workspaces once this app starts calling the real API in Phase 1/4 — not needed for the current placeholder page.
