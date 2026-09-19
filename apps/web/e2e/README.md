# End-to-end tests

A real browser against a real running stack. **Local only -- not in CI**: they need `apps/api`, a queue, `ffmpeg` on PATH, and (for the flow specs) `apps/worker` with its ML dependencies and two real solo dance videos.

## What's here

| Spec | Needs | Covers |
|---|---|---|
| `auth.spec.ts` | API | The studio gate redirect, register -> auto-login, wrong-then-right password |
| `upload.spec.ts` | API | The upload form refuses to continue until both videos are supplied |
| `responsive.spec.ts` | API | No page scrolls sideways at 390 / 768 / 1440px (landing, login, register, upload in both reference modes) |
| `analysis.spec.ts` | + worker, real videos | The whole product path: real clips attached to the real `<input type="file">`, real worker, a real score and timeline in the browser |
| `flows.spec.ts` | + worker, ffmpeg, real videos | A non-YouTube reference link is refused before any download; a video with nobody in it is rejected with a reason; a *reference* video with nobody in it is rejected and the reason says it's the reference; a two-person video goes to the pick page, then to a real result (with an overflow check at three widths on the pick and results pages) |

Not covered: the YouTube-link *happy path* (it would download a real video from the network), other browsers, and the OS file-picker dialog itself (Playwright drives the real file input, not the dialog).

## How the suite is structured

Registration is rate-limited (5 per hour per IP), so tests don't each register a user. `auth.setup.ts` registers **one** shared user and saves its session; the `signed-in` project reuses it. Only `auth.spec.ts` (project `anonymous`) starts logged out. A full run registers about 3 users. The limiter is in memory, so restarting the API resets it -- do that if you're re-running repeatedly and see "Too many requests".

## Running them

Start the stack (no Docker: see the "No Docker?" note in `apps/worker/README.md`). The suite has been run against both SQLite and a real Postgres (`pip install pgserver`; point `DATABASE_URL` for the API and worker at `postgresql+psycopg2://postgres@127.0.0.1:<port>/<db>`). One shared absolute `DATABASE_URL` for the API and worker, and `REDIS_URL=redis://127.0.0.1:6379` (not `localhost` -- IPv6-first resolution hangs on Windows):

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

The specs that need only the API run without the video variables: `npx playwright test auth upload responsive`. Specs that need videos or ffmpeg skip themselves with a reason when those are missing.

The browser defaults to the Edge already installed on Windows so nothing is downloaded; set `CADENCE_E2E_CHANNEL=chrome` for Chrome, or install Playwright's own browsers and change the config.

## Gotchas

- **The machine sleeping mid-run fails the long tests.** Playwright's timeouts are wall-clock, so if the computer suspends during the ~2 minute analysis, the test times out on wake even though nothing is wrong (seen once: the worker and the page's polling both froze for 8 minutes, and the test failed the moment it woke). Re-run it.
- The first analysis after installing the worker's dependencies makes Ultralytics auto-install `lap` and print "Restart runtime"; it still completes.
