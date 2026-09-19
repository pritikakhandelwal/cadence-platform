# Product decisions and why

Short record of decisions that shape the roadmap, so nobody re-litigates them mid-build.

## Song-driven choreography teaching → curated content, not generative

**Ask:** "let users pick a song and be taught the choreo via animation."

**Decision:** Ship as *pick a song → match BPM/genre → recommend a curated, human-choreographed phrase → play back a speed-adjustable 3D reference animation*. Do **not** build a system that invents novel choreography for an arbitrary song.

**Why:**
- Generating movement for arbitrary music is its own research project (music-to-dance generation, e.g. Bailando/EDGE-style models) — months of work, and prone to producing physically implausible or culturally incoherent movement, which is disqualifying for codified forms like Bharatanatyam or Kathak.
- Storing choreography tied to arbitrary copyrighted commercial audio is a licensing risk. BPM/genre matching against a curated catalogue (or the user's own uploaded audio, analyzed but not stored) avoids that.
- The curated version reuses the same R3F skeleton renderer already required for scoring (Phase 3/4) — no separate rendering pipeline.

This lives in Phase 5 + Phase 6 of [`ROADMAP.md`](../ROADMAP.md).

## YouTube link for the professional reference video → build it, scoped narrow

**Ask:** "integrate an option of putting a YouTube link for the professional dance section" (instead of only uploading a file).

**Decision:** `POST /analyses` accepts `professional_video_url` as an alternative to `professional_video` (exactly one of the two, not both, not neither). Server downloads it with `yt-dlp`, then runs it through the *same* validation (`ffprobe` duration/codec checks) as an uploaded file. Restricted strictly to `youtube.com`/`youtu.be` hosts over `http`/`https` — never an arbitrary URL.

**Why the restriction, specifically:**
- Downloading and storing third-party YouTube content server-side to compare against a user's own dance is a real copyright/ToS gray area — YouTube's ToS generally restricts downloading outside their own offline feature. Built anyway, since many "practice against a reference" apps operate in this same space for personal, non-redistributed use, but this is a real exposure, not a solved one — worth knowing if this ever needs a legal review before wider release.
- A generic "fetch this URL" endpoint on a server is a classic SSRF vector — it can be used to probe internal network addresses, cloud metadata endpoints, or `file://` paths. Restricting to a fixed host allowlist *and* to `http`/`https` schemes closes that off. (A test that used a real `youtube.com` URL without mocking the downloader caught a real gap here during development: the host check alone passed `ftp://youtube.com/...`, since `urlparse` extracts a hostname regardless of scheme — the scheme check was missing. Fixed, and a test-suite safety net now makes any test that reaches the real downloader unmocked fail loudly instead of silently downloading real content, after exactly that happened once — see `apps/api/tests/conftest.py`.)
- Reusing `validate_saved_video` (the same `ffprobe` check an uploaded file goes through) rather than trusting `yt-dlp`'s metadata means a YouTube link can't bypass the platform's normal duration/codec/size expectations just by arriving a different way.

## Dance-form auto-detection → confirmable suggestion, gated on lock-on

**Ask:** "detect the dance form automatically."

**Decision:** Build it, but last (Phase 8), and only as a confidence-scored suggestion the user confirms or overrides — never a silent switch of scoring rubric.

**Why:**
- Classification quality is gated by tracking quality. Wrong keypoints → wrong label → wrong rubric applied → confidently wrong feedback, which is worse than no label.
- Labeled data for Indian classical forms is scarce publicly; you're mostly self-collecting, which is slow.
- Building this before lock-on (Phase 2) is reliable is explicitly called out as a project-killing sequencing mistake in Section 7 of the roadmap.

## Shared DB and workspace packages, not a callback API

**Ask (implicit):** once `apps/worker` needs to write an analysis result somewhere `apps/api` can read it back from, how do the two processes share that state?

**Decision:** both talk to the same Postgres/SQLite directly, via new shared packages (`packages/db` for the SQLAlchemy models, `packages/workspace` for the per-analysis file paths) rather than an HTTP callback from worker to API.

**Why:**
- The roadmap's own architecture diagram (§2) already draws both the API and the workers connecting to PostgreSQL directly — a callback API would be inventing a different architecture than the one already decided.
- A callback endpoint is a second surface to authenticate, version, and keep in sync with the DB schema, for no benefit over just writing the row directly when both processes already have `DATABASE_URL`.
- `packages/workspace` exists for the same reason on the filesystem side: `apps/api` writes uploaded videos, `apps/worker` needs to read the exact same files to run detection/pose on them. Its default runtime directory is resolved relative to the *package's* location in the repo, not whichever app imports it, so the two processes agree on the same path without either one setting `CADENCE_RUNTIME_DIR` by hand for local dev.
- Both packages started as private modules inside `apps/api` in Phase 1, when only the API needed them. Moved out in Phase 2 the moment a second process needed the same logic — not extracted preemptively "in case it's needed later."

## SQLite → Postgres

Legacy app uses SQLite (fine for a single-process demo). Production target is Postgres per the locked architecture — SQLite does not survive concurrent writers safely. Migration happens in Phase 1/7.

## MediaPipe → YOLO + tracker + RTMPose/ViTPose

Legacy app runs MediaPipe on the full frame. This breaks on multi-person shots, mirrors, and occlusion — exactly the real-world conditions dance video has. Phase 2 replaces this with detect → track → crop → pose. MediaPipe stays only as a fallback for a future live-webcam v1 (Phase 8).

## Scoring formula: a transform over a principled feature, not "no formula"

**Tension:** the roadmap's Section 7 explicitly calls out `100 - similarity*2`-style formulas as the fake score to replace, but *any* score is ultimately some function mapping an error measure to a number -- so what makes one formula legitimate and another not?

**Decision:** `score = 100 * exp(-mean_abs_angle_error_deg / TAU)`, with `TAU` chosen and documented against one stated reference point (a 20-degree average joint-angle error gives 50%), computed over normalized joint angles + DTW alignment, not raw pixel distance.

**Why this isn't the same anti-pattern with extra steps:** the legacy formula's problem was never "it's a formula" -- it's that it ran on unaligned, unnormalized raw coordinates, so the *number it fed into* wasn't measuring anything real. Fixing the feature (rotation/scale/translation-invariant joint angles) and the alignment (DTW, not frame-index-order) is the actual fix. The transform on top still has to be *some* function, and choosing one with a named, checkable meaning ("half credit at 20 degrees") is the difference between "a formula" and "an arbitrary formula" -- not the presence of a formula at all.

## Issue-type checklist (torso lean, occlusion, missed/extra move, low energy, balance) → no new schema field for arm-vs-leg

**Ask:** a claude.ai/design questionnaire for the Arena UI asked which issue categories to surface, including "arm position" and "leg/footwork" as if they might be separate issue types alongside torso lean, occlusion, missed/extra move ("tempo"), low energy, and balance wobble.

**Decision:** built real backend detection for torso lean (`angle`, no longer suppressed), occlusion, tempo, energy, and balance as five distinct `IssueType` values — but did **not** add separate arm/leg issue types. The existing `angle` issue's `joint` field already names the specific joint (`left_elbow`, `right_knee`, ...), and a UI can group by "arm" vs. "leg" from that name alone (see `JOINT_ANGLE_TRIPLES` in `apps/worker/worker/pipeline/features.py` for the fixed set of names). Adding `IssueType.arm`/`IssueType.leg` would duplicate information the `joint` field already carries, for a distinction that's really a UI grouping choice, not a different kind of measurement.

**Why this matters for the eventual Arena UI:** if the design needs an "arm issues" vs. "leg issues" filter or icon, do it by pattern-matching `joint` client-side (`elbow`/`shoulder` → arm, `knee`/`hip`/`ankle` → leg), not by asking the backend to add a type. The backend's job is to say *what* differs and *by how much*; how the UI buckets that for display is a presentation concern.

**Issue ordering within a window: technique feedback before data-quality caveats.** Adding `occlusion` initially put it *ahead* of `angle` in each window's issue list, on the theory that "we couldn't see this joint" is the more fundamental fact. That was wrong in practice: it made `segment.issues[0]` ("the top issue") an irrelevant occlusion notice on a real clip more often than not, because *some* joint dips below the confidence threshold in part of a window fairly often, for reasons that have nothing to do with whichever joint is actually wrong. Caught by the real-motion planted-error regression test, whose attribution accuracy collapsed from 82% to 20% purely from this reordering — all 59 synthetic unit tests stayed green, because none of their fixtures happened to combine a planted error with unrelated occlusion in the same window. Fixed by putting `angle` first: it names a specific joint and a specific error, which is the actual technique feedback a dancer acts on; occlusion/balance/tempo/energy/timing are secondary context, not competing headlines. General lesson reaffirmed, not new: a synthetic test suite passing is necessary, not sufficient — this project's real-footage integration pass exists specifically to catch exactly this kind of thing, and did.

## 2D pose comparison conflates real angle differences with camera viewpoint -- known, not fixed

**Found:** scoring the two real available clips (`professional_dance.mp4`, `user_dance.mp4`) against each other, hip-joint angle differences stayed large (40-90 degrees) even after adding confidence-masking for low-visibility keypoints (see `apps/worker/README.md`'s Phase 3 section). Checked actual RTMPose confidence for those hip keypoints: ~0.6, moderate, not clearly garbage -- so this isn't (only) a masking problem.

**Why, and why it's not being patched now:** RTMPose-m here is 2D-only. A joint-angle triple computed from 2D image coordinates is invariant to in-plane rotation, but *not* to the camera's viewing angle -- the same 3D hip pose, filmed from two different camera angles (which is exactly what two independently-recorded phone videos would have), can legitimately project to two different 2D angles. This pipeline cannot currently tell "the dancer's hip is genuinely at a different angle" apart from "the camera is looking at the same hip from a different side." That's a real, unresolved limitation, not a bug -- fixing it means 3D pose (the roadmap's own Phase 8: "Optional SMPL mesh for nicer 3D", and 3D is explicitly deferred there for a reason). Tuning the confidence threshold or the angle-issue cutoff to make hip errors disappear on this *one* clip pair would be fitting the eval to itself, which is exactly what the roadmap's "don't tune against guesses, tune against the eval set" principle (Phase 2, dataset section) warns against -- there's no eval set yet, so there's nothing legitimate to tune against.

**What this means in practice for now:** treat elbow/shoulder issues as more trustworthy than hip/knee issues until either 3D pose exists or there's a real multi-clip eval set to check hip-angle reliability against. Don't hide this by suppressing hip issues outright -- that would substitute a different unvalidated guess for the current one.

## Wiring `apps/web` to `apps/api`: a `file:` dependency, not npm workspaces

**Ask (implicit):** `apps/web`'s own README said `@cadence/schema` "gets wired in via npm workspaces once this app starts calling the real API" -- that point arrived this session.

**Decision:** added `"@cadence/schema": "file:../../packages/schema/typescript"` directly to `apps/web/package.json`, plus `transpilePackages: ["@cadence/schema"]` in `next.config.ts` (needed because the schema package ships raw `.ts` source with no build step, and Next's compiler skips `node_modules` by default). Did **not** add a root-level `package.json` with npm workspaces, despite that being what the README described.

**Why:** `.github/workflows/ci.yml` currently installs `apps/web` and `packages/schema/typescript` as two fully independent npm projects (`working-directory` + plain `npm install` in each). A root workspace would change that installation topology for both CI jobs, for a benefit (workspace-aware installs) this particular task didn't need -- importing one package's types. A `file:` dependency gets the same real linkage (a symlink in `apps/web/node_modules`) with a one-line change and zero effect on how CI already installs the other two packages. Worth revisiting if a third package needs the same treatment and the duplication starts to hurt.

## Auth is cookie-only; `apps/web` needed CORS added to `apps/api`, not a token store

**Found:** `apps/api`'s auth (`POST /auth/login`) sets an httponly session cookie and has no bearer-token path at all -- confirmed by reading `apps/api/app/deps.py` and `routers/auth.py` before writing any frontend code, rather than assuming a token existed. `apps/api/app/main.py` also had no CORS middleware at all, which silently doesn't matter until a browser on a different origin (`apps/web` on :3000) tries to call it.

**Decision:** added `CORSMiddleware` to `apps/api/app/main.py` with an explicit `allow_origins=["http://localhost:3000"]` and `allow_credentials=True`, and made every `apps/web` fetch call send `credentials: "include"`. Did not add any client-side token storage.

**Why the explicit origin, not `"*"`:** the fetch spec forbids combining a wildcard origin with credentialed requests -- `allow_origins=["*"]` plus `allow_credentials=True` fails silently (the browser just refuses to expose the response), so this had to be an explicit list from the start. This is a real thing to revisit before any real deployment: the allowed origin is hardcoded, not read from an env var, which is fine for local dev and wrong for anything else -- see `apps/web/README.md`'s "What's not real yet."

## A crashed analysis is recorded as `rejected`, not left `queued`

**Found:** reading `apps/worker/worker/tasks.py` while writing end-to-end tests for the unhappy paths: neither job had any exception handling. If detection, pose extraction or scoring threw (a video `ffprobe` accepts but OpenCV can't decode, an ML error, a bad reference clip), arq marked the *job* failed but the *analysis row* stayed `queued` forever -- and the UI polled it forever, telling the person it "usually takes under a minute." Reproduced deterministically with a fake pipeline (`apps/worker/tests/test_task_failures.py`; 4 of its 5 tests fail on the old code).

**Decision:** both jobs now catch `Exception`, log the traceback, and write a terminal result to the row -- status `rejected`, reason "Something went wrong on our side while analyzing this video. Please try again." The frontend already turns `rejected` into a dismissible notice and a way back to upload, so no frontend change was needed for the crash path itself. Separately, the processing page now stops promising "under a minute" after 3 minutes (`apps/web`), because a *dead* worker (as opposed to a crashing job) still leaves a row stuck.

**The tradeoff, stated plainly:** `rejected` means "your input was bad," and this isn't that -- it's our fault, and the message says so. A distinct `failed` status would be cleaner (the UI could offer "retry" rather than "fix your video," and metrics could separate infrastructure failures from bad uploads), but it would change the frozen `AnalysisResult` contract in both `packages/schema` languages and every consumer, which wasn't warranted for this fix. Worth revisiting if failures need different handling or reporting. Not covered: a worker that dies or is killed mid-job never reaches this code, so that row still stays `queued`.

## Timezone-aware datetime columns, and SQL NULL (not JSON `null`) for empty JSON

**Found:** by running the API suite and then the browser suite against a real Postgres 16 (no Docker here, so via the self-contained `pgserver` pip package) -- neither showed up on SQLite.

**1. Datetimes.** Every `DateTime` column was timezone-naive, but the code writes timezone-aware UTC values and reads naive ones back as UTC. On Postgres, an aware value going into `TIMESTAMP WITHOUT TIME ZONE` is first converted using the *server session's* time zone, then the offset is dropped -- so on a server not set to UTC the stored value is wrong, and the read path ("assume UTC") silently propagates it. Reproduced: on a UTC+5:30 server, session expiry and lockout end came back **5h30m off** (`tests/test_datetime_roundtrip.py`). It hid because most Postgres servers default to UTC. **Decision:** every `DateTime` is `timezone=True` (TIMESTAMPTZ on Postgres; SQLite ignores the flag and still returns naive UTC, which the auth code already treats as UTC). No migration path was written because no Postgres database is known to exist yet -- one created earlier would need `ALTER COLUMN ... TYPE timestamptz` (with the right `USING` for its server's zone). My first pass at this changed six of seven columns and missed `expires_at` (its declaration had no trailing comma for my find-and-replace to match); the test caught it, which is the reason to keep it.

**2. JSON null.** Explicitly setting `result` or `pending_lock_data` to `None` stored the JSON literal `null`, not SQL `NULL`, on both SQLite and Postgres. The application treats both as empty so nothing broke, but it contradicted the `Analysis` docstring ("NULL while queued") and any `WHERE pending_lock_data IS NOT NULL` query (e.g. finding analyses awaiting a dancer pick) would have returned finished ones. **Decision:** `JSON(none_as_null=True)`; no DDL change. Guarded by `tests/test_json_null.py`.

**CI:** the API job now also runs the suite against a Postgres service container whose server is set to a non-UTC zone (`CADENCE_TEST_DATABASE_URL`), so the timezone test has teeth there. That workflow change is unverified -- it parses as YAML, but it hasn't run on GitHub Actions.

## Tracker and pose libraries: integrate, don't reimplement

**Decision:** use `ultralytics`'s built-in `.track()` (which already bundles YOLO detection with a ByteTrack/BoT-SORT tracker) instead of hand-rolling ByteTrack, and use `rtmlib` (RTMPose over onnxruntime) instead of installing the full OpenMMLab stack (`mmcv`/`mmdet`/`mmpose`).

**Why:**
- Reimplementing ByteTrack correctly (Kalman filter, cascade matching, track lifecycle) is a research-engineering project on its own — the roadmap already scopes Phase 2 as 6-8 weeks for a reason; spending that budget re-deriving a tracker that ships free with the detector would be the wrong 6-8 weeks.
- The full `mmcv`/`mmdet`/`mmpose` stack is notoriously version-fragile (compiled CUDA ops, tight pinned versions across three packages). `rtmlib` runs the same RTMPose ONNX-exported weights through plain `onnxruntime`, with no compiled-extension version matrix to fight — the practical choice for a small team, not a compromise on the model itself.
- Both choices are swappable later: if RTMW (whole-body, for Indian classical hand detail) or a different tracker outperforms these on the eventual 30-clip eval set, `pipeline/pose.py` and `pipeline/detection.py` are the only two files that would need to change — `pipeline.py`'s orchestration and everything downstream (Phase 3 scoring) doesn't care which library produced the keypoints.
