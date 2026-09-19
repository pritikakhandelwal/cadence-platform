# End-to-end tests

A real browser against a real running stack. **Local only -- not in CI**: they need `apps/api`, a queue, and (for `analysis.spec.ts`) `apps/worker` with its ML dependencies and two real dance videos.

## What's here

- `auth.spec.ts` -- needs only `apps/api` + `apps/web`. The studio gate redirect, register -> auto-login, wrong-then-right password, and the upload form's validation.
- `analysis.spec.ts` -- the whole product path through the actual UI: register, attach two real videos to the real `<input type="file">`, submit, watch the processing page poll, and assert a real score and timeline render. Skipped unless the two env vars below are set.

## Running them

Start the stack (no Docker: see the "No Docker?" note in `apps/worker/README.md`). One shared absolute `DATABASE_URL` for the API and worker, and `REDIS_URL=redis://127.0.0.1:6379` (not `localhost` -- IPv6-first resolution hangs on Windows):

```bash
# from apps/worker, in a venv with api + worker requirements and fakeredis
python scripts/dev_fake_redis.py &
DATABASE_URL=sqlite:///C:/abs/path/e2e.db REDIS_URL=redis://127.0.0.1:6379 python scripts/dev_worker_no_info.py &
# from apps/api
DATABASE_URL=sqlite:///C:/abs/path/e2e.db REDIS_URL=redis://127.0.0.1:6379 uvicorn app.main:app --port 8000 &
```

Then, from `apps/web` (the dev server is started for you if it isn't already running):

```bash
CADENCE_E2E_USER_VIDEO=C:/path/user.mp4 CADENCE_E2E_REFERENCE_VIDEO=C:/path/reference.mp4 npm run e2e
```

`auth.spec.ts` alone needs just the API: `npx playwright test auth`.

The browser defaults to the Edge already installed on Windows so nothing is downloaded; set `CADENCE_E2E_CHANNEL=chrome` for Chrome, or install Playwright's own browsers and change the config.
