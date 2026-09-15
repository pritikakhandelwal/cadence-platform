# Cadence — Final Roadmap

**Product:** A broadcast-grade dance coaching platform.
**Bar:** International product quality. SIH-finalist technical depth. FAANG-interview ownership.

**North star**

> Lock onto the intended dancer in messy video, reconstruct motion, align it to a reference, and return timestamped, body-part-specific coaching a dancer can actually use — then route them to the next form, phrase, and track.

If a feature does not improve **lock-on**, **honest scoring**, **actionable feedback**, or **the arena experience**, it waits.

---

## 1. Research basis (why this stack, not MediaPipe + one DTW number)

### Pose (2025–2026 production consensus)

Industry has converged on four families: OpenPose (legacy), MediaPipe/BlazePose (mobile), **RTMPose** (production speed/accuracy), **ViTPose / ViTPose++** (accuracy when you have GPU).

| Model | Role in Cadence | Why |
|---|---|---|
| **YOLO / RTMO** | Person detect + optional pose | Multi-person, real-time |
| **ByteTrack or BoT-SORT** | Identity across frames | Dance has turns, drops, brief occlusion |
| **RTMPose-m / RTMW** | Default 2D / whole-body pose | ~75.8 AP, 90+ FPS on CPU; whole-body (hands/face) matters for Indian classical and popping. RTMPose is the OpenMMLab production workhorse. |
| **ViTPose-L/H** | High-accuracy batch path | ~80.9 AP; use when quality > latency (uploaded studio analysis). |
| MediaPipe | Fallback / live webcam v1 only | Fast, not accurate enough for "international coaching" |

**Pipeline (top-down, not full-frame MediaPipe):**
detect people → track IDs → user locks dancer → crop → pose on crop → temporal smooth → features.

This is how you survive friends in frame, mirrors, and judges in the background. Dance archives specifically break naive pose systems (unusual poses, costumes, fast rotation, occlusion). A 2025 dance-video paper had to combine sports-style 3D pipelines because generic pose failed.

Known HPE failure modes you must design for: multi-person interaction, **temporal jitter**, domain shift (bedroom vs stage), and physically implausible skeletons.

### Comparison / scoring

Raw XYZ DTW on unnormalized landmarks is not coaching. Literature on traditional dance matching uses **normalized DTW on skeleton features**, not a single distance dressed up as "pose accuracy."

Cadence scoring stack:

1. Procrustes / torso-center + scale (+ yaw) normalization
2. Joint angles + bone directions (rotation-aware; downweight noisy Z)
3. **Soft-DTW or classic DTW on the feature sequence** for *alignment*
4. Segment the warping path → per-window errors
5. Report **confidence** (track quality, keypoint vis, occlusion)

That is the difference between a hackathon toy and a system you can defend.

### Product / visual research

Red Bull's dance products (BC One, E-Battle) are **broadcast arenas**, not dashboards: full-bleed video, fighter identity, impact graphics, live HUD. Cadence should steal that grammar (dark stage, one accent color, score slam, lower-thirds), not the logo.

---

## 2. Locked architecture

```text
┌──────────────┐     ┌──────────────┐     ┌─────────────────────┐
│  Next.js web │────▶│  FastAPI     │────▶│  Redis queue        │
│  Arena UI    │◀────│  BFF / auth  │◀────│  Celery/Arq workers │
└──────────────┘     └──────────────┘     └─────────┬───────────┘
        │                    │                      │
        │                    ▼                      ▼
        │             PostgreSQL              YOLO + tracker
        │             object store            RTMPose / ViTPose
        │             (videos, overlays)      FFmpeg + 3D export
        ▼
   R3F 3D skeleton + Rive HUD
```

| Layer | Choice | Do not use |
|---|---|---|
| Web | Next.js 15, TypeScript, Tailwind, shadcn (custom Arena theme), Framer Motion, R3F, TanStack Query | Streamlit, default purple SaaS |
| Motion design | Figma (system) + Rive (HUD) + AE (trailer only) | 80 Figma artboards, no code |
| API | FastAPI, Pydantic, OpenAPI | Django-for-ML, Streamlit callbacks |
| Jobs | Redis + Arq/Celery | In-request MediaPipe |
| DB | PostgreSQL + migrations | SQLite in production |
| Files | S3-compatible, UUID workspace per analysis | `output/overlay.mp4` in repo |
| Auth | Better Auth / Auth.js, Argon2, rate limit | `st.session_state.logged_in` |
| Pose | YOLO → BoT-SORT/ByteTrack → RTMPose (default) / ViTPose (quality) | MediaPipe-only forever |
| Video | FFmpeg probe + transcode | Hardcoded 720×1280 |

Monorepo: `apps/web`, `apps/api`, `apps/worker`, `packages/schema`.

**One contract rules the product:** `AnalysisResult`. Frontend, API, worker, and Figma all speak it.

---

## 3. Design system (Red Bull arena, not SaaS)

**Figma is the hub, not the look.** The look is coded.

| Token | Spec |
|---|---|
| Void | Near-black, grain, crushed blacks |
| Ember | One accent (competition red) **or** Voltage (acid yellow) — pick one |
| Ice | Scores, timestamps, technical readouts |
| Type | Condensed display for `84.2`; clean grotesque for UI |
| HUD | Sports lower-third, not cards with drop shadows |
| Motion | Slam / whoosh / lock-on; no gentle corporate fades |
| 3D | Dancer as a light-rigged figure on a dark floor |

**Figma file (max):** tokens, 12 components, 10 screens, all states (uploading, analyzing, multi-person pick, reject, empty).
**Rive:** score burst, tracking lock, button impact.
**Three.js:** real skeleton, error heat, orbit camera.
**After Effects:** 20–30s SIH trailer only.

---

## 4. Canonical `AnalysisResult` (build this first)

```text
analysis_id
user_id
status: queued | running | needs_dancer_pick | complete | rejected
tracking: { confidence, reliable_frame_pct, person_count, lock_id }
overall: { score, method, version }
segments[]: { t0, t1, score, issues[], confidence }
issues[]: { joint, type: angle|timing|path, magnitude, message }
artifacts: { overlay_url, skeleton_3d_url, thumbs }
quality_gate: { passed, reasons[] }
```

No page may invent `pose_accuracy = similarity + 3`. If it is not in this object, it does not exist.

See [`packages/schema`](packages/schema) for the frozen TypeScript + Pydantic definitions.

---

## 5. Phased roadmap

Durations assume **1–2 serious builders**. Quality over calendar. Total to "international demo": ~9–12 months. Full platform: ~15–18.

### Phase 0 — Foundation (3 weeks)

**Purpose:** Stop being a zip of scripts.

- Monorepo, lint, typecheck, CI
- Central config, no hardcoded paths
- `.gitignore` for venv, videos, weights, db
- Real README (setup, models, FFmpeg, env)
- pytest for current DTW / auth / validation (pin the old behavior before you replace it)
- Freeze `AnalysisResult` schema in TypeScript **and** Python

**Done when:** `web` hello-route + `api` health + one worker echo job pass CI. Old Streamlit can still run in a `legacy/` folder until Phase 4 cuts it.

**Risk:** Rewriting UI before the schema exists. Don't.

---

### Phase 1 — Trust (4 weeks)

**Purpose:** Concurrent users, safe files, real accounts.

- UUID workspace per analysis; path jail
- Upload validation: magic bytes, size, duration, FFmpeg probe, codec
- FFmpeg missing → explicit product error
- Cleanup job (abandoned workspaces)
- Argon2 only; upgrade or force-reset legacy SHA-256
- Rate limit + lockout
- Escape all user strings; `unsafe_html` banned
- Persist analysis rows (not session-only)

**Done when:** two parallel uploads cannot collide; garbage video fails with a human reason; refresh does not destroy a finished analysis.

**Eval:** adversarial uploads (renamed `.exe`, 0s video, 4K 20min, no person).

---

### Phase 2 — Lock-on (6–8 weeks) ★ technical heart

**Purpose:** The system knows *who* the dancer is.

- YOLO person detect
- ByteTrack or BoT-SORT
- Multi-person UI: pick fighter, then lock
- Short-gap interpolation; drop track if quality collapses
- Pose **on crop only** (RTMPose-m default)
- One-Euro or Savitzky–Golay smoothing (kill jitter)
- Quality metrics: ID switches, fragmentations, % frames with dancer, mean keypoint conf
- Reject with reasons: "dancer lost 38% of frames", "two people crossed, lock failed"

**Done when:** a clip with a second person + a mirror is handled, or clearly refused.

**Eval (do this or it is not FAANG-level):**

| Metric | Target v1 |
|---|---|
| MOTA / IDF1 on a 20-clip internal set | Track, even if numbers are modest |
| Reliable-frame % on solo bedroom clips | ≥ 90% |
| False lock on mirror | 0 on the test set |
| Time-to-first-lock | < 2s of video |

Dataset: film 30 clips yourself (solo, duo, mirror, occlusion, Bharatanatyam hasta, hip-hop freeze). Do not wait for a public dance MOT set.

---

### Phase 3 — Coaching intelligence (6 weeks) ★ product heart

**Purpose:** Replace the fake score.

- Torso-relative features; angle set (elbow, knee, hip, shoulder, spine)
- Downweight Z; upweight angles in rotational windows (yaw-rate high)
- DTW/Soft-DTW on features → warping path
- Segment path into 1–3s windows
- Joint-level residuals → messages with timestamps
- Structured result only
- 2D overlay + 3D joint error heat

**Target output**

```text
Overall 84.2%    Tracking 93%    Reliable frames 96%

00:12.4–00:15.1
• Left elbow over-extended ~18°
• Transition 0.3s early
• Hip rotation lagging shoulders
```

**Done when:** a dancer can fix one thing from the report without you explaining the math.

**Eval:** 10 phrase pairs (good vs known-bad). Bad must score lower **and** the top issue must match the planted error (elbow, timing, or hip) ≥ 70% of the time. If not, the model is still a toy.

---

### Phase 4 — Arena frontend (6 weeks, overlap last 3 of Phase 3)

**Purpose:** It looks like a world final.

Routes:

| Route | Job |
|---|---|
| `/` | Cinematic lander, one CTA |
| `/studio` | Upload, fighter pick, live job HUD |
| `/analysis/[id]` | Score slam, timeline, feedback |
| `/analysis/[id]/skeleton` | 3D stage |
| `/explore` | 10 form fight-cards |
| `/learn/[form]/[phrase]` | Counts, reference, common mistakes |
| `/music` | Track → recommended forms |
| `/you` | History, skill map, rematch vs last run |

Implementation notes:

- Video is full-bleed; UI is overlay
- WebSocket job progress (never a frozen page)
- Timeline synced to segments
- Rive for lock-on + score
- R3F skeleton, not a CSS stick figure
- Mobile: review + explore first; studio prefers landscape

**Done when:** a 3-minute silent demo (no voiceover) still feels expensive.

Cut Streamlit from the product path here. Keep `legacy/` only for algorithm A/B.

---

### Phase 5 — Learning platform (5 weeks)

**Note (song-driven teaching, added after Phase-0 kickoff):** "pick a song → learn choreo" ships as *curated content + BPM/genre matching*, not generative choreography. A human choreographs each phrase once; the system recommends it for songs whose BPM/genre fit, and plays it back as a speed-adjustable 3D animation. Do not attempt to generate novel choreography for an arbitrary song — that is an unscoped research project (music-to-dance generation) and a licensing risk if tied to copyrighted commercial audio. See [`docs/decisions.md`](docs/decisions.md).

- 10 forms: Bharatanatyam, Kathak, Bhangra, Bollywood, Hip-hop, Contemporary, Ballet, Salsa, Jazz, K-pop
- Each form: 1 hero, 2–3 beginner phrases, counts, difficulty, energy, region, **licensed or original media only**
- Filters: difficulty, energy, region, solo/group, style
- Progress from real `AnalysisResult`s, not XP = `total * 100`
- Rematch: same phrase, overlay last vs now
- Each phrase ships with a pre-authored, retargetable 3D reference animation (reuses the Phase 4 R3F skeleton renderer) — not just a reference video

**Done when:** discover → learn counts → analyze → see one joint improve.

---

### Phase 6 — Music intelligence (3–4 weeks)

- Curated catalogue: BPM, energy, meter, mood, genre
- Rule-based compatibility matrix (explainable)
- Rank phrases by music + user level
- Optional later: librosa / BeatNet on user audio

Example:

```text
128 BPM · energetic · 4/4
→ Bhangra, Hip-hop, Salsa
Reason: tempo and pulse density match these forms.
```

No black-box "AI recommends" without a sentence.

---

### Phase 7 — Production (4 weeks)

- Postgres primary, backups, migrations
- Workers autoscale; model weights cached per process
- Object storage; signed URLs
- Sentry + job metrics (queue time, fail rate, GPU)
- GitHub Actions: lint, typecheck, pytest, Playwright smoke
- Deploy docs; no secrets in source
- Load test: 20 concurrent analyses

**Done when:** restart mid-job does not corrupt data; failed jobs are visible and retryable.

---

### Phase 8 — Research track (optional, after 0–7)

Only if the core is elite:

- Whole-body hands for classical
- Live camera studio (RTMPose-s / YOLO-Pose)
- **Dance-form auto-classification** on **tracked, normalized** sequences, with a confirmable, confidence-scored suggestion the user can override — never a silent rubric switch. Gated on lock-on being reliable first (see Section 7 risk note).
- Teacher / class mode
- Optional SMPL mesh for nicer 3D (not required for scoring)

Auto-classification before lock-on is reliable is how projects die.

---

## 6. Priority order (non-negotiable)

```text
1. Schema + isolation + validation + tests
2. Auth / XSS / persistence
3. Detect → track → lock → quality gate
4. Normalized features + alignment + timestamped feedback
5. Arena UI (3D + timeline + HUD)
6. Catalogue + learn + rematch
7. Music recommendations
8. Production hardening
9. Live / classifier / teacher mode
```

---

## 7. Why this beats the current project

| Axis | Current | This roadmap |
|---|---|---|
| Pose | MediaPipe on full frame | Detect–track–crop; RTMPose / ViTPose |
| Identity | None | Lock + re-ID + reject |
| Score | `100 - d*2` and invented metrics | Alignment path + angles + confidence |
| Feedback | Generic text | Timestamped joints |
| UI | Streamlit HTML | Arena HUD + 3D |
| State | Session | Postgres `AnalysisResult` |
| Jobs | Blocking | Queue |
| Files | Shared names | UUID + object store |
| Design | Pages | Figma system + Rive + R3F |
| Proof | None | MOT-style + planted-error tests |
| Demo | Charts | Score slam on a dark stage |
| Story | "We used MediaPipe" | "We built lock-on, alignment, and coaching under production constraints" |

---

## 8. 30 / 90 / 180 days

| Window | You should be able to show |
|---|---|
| **30 days** | Schema, auth, isolated upload, FFmpeg validation, CI, Figma tokens + 10 frames |
| **90 days** | Lock-on on messy video, honest overall + 3 timestamped issues, Next.js studio playing a real result |
| **180 days** | Full arena, 10 forms seeded, rematch, music rules, 3-min trailer, SIH-ready demo |

---

## 9. SIH / FAANG narrative (use this, unchanged)

**Problem.** Dancers get a vague score. Real videos have extra people, mirrors, and occlusion. No one tells them *when* and *which joint*.

**Method.** Top-down tracking, crop-level RTMPose, temporally smoothed features, DTW as alignment, segment residuals, quality gates.

**Evidence.** Reliable-frame %, planted-error hit rate, before/after on the same phrase.

**Product.** Broadcast studio, not a notebook.

That is the international version of Cadence.

---

## 10. Hard rules

- Do not patch Streamlit into this look.
- Do not train a style model in month 1.
- Do not add an LLM coach that cannot point at a timestamp.
- Do not ship Explore as pretty cards while Studio still freezes.
- Licensed media only.
- One accent color.
- If you cannot measure it, you may not claim it.

---

Next implementation artifact: the **exact** `AnalysisResult` TypeScript + Pydantic models, SQL tables, and the 10-screen Figma inventory mapped to Next.js routes. That is Phase 0, day 1.
