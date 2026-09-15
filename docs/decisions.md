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

## Dance-form auto-detection → confirmable suggestion, gated on lock-on

**Ask:** "detect the dance form automatically."

**Decision:** Build it, but last (Phase 8), and only as a confidence-scored suggestion the user confirms or overrides — never a silent switch of scoring rubric.

**Why:**
- Classification quality is gated by tracking quality. Wrong keypoints → wrong label → wrong rubric applied → confidently wrong feedback, which is worse than no label.
- Labeled data for Indian classical forms is scarce publicly; you're mostly self-collecting, which is slow.
- Building this before lock-on (Phase 2) is reliable is explicitly called out as a project-killing sequencing mistake in Section 7 of the roadmap.

## SQLite → Postgres

Legacy app uses SQLite (fine for a single-process demo). Production target is Postgres per the locked architecture — SQLite does not survive concurrent writers safely. Migration happens in Phase 1/7.

## MediaPipe → YOLO + tracker + RTMPose/ViTPose

Legacy app runs MediaPipe on the full frame. This breaks on multi-person shots, mirrors, and occlusion — exactly the real-world conditions dance video has. Phase 2 replaces this with detect → track → crop → pose. MediaPipe stays only as a fallback for a future live-webcam v1 (Phase 8).

## Tracker and pose libraries: integrate, don't reimplement

**Decision:** use `ultralytics`'s built-in `.track()` (which already bundles YOLO detection with a ByteTrack/BoT-SORT tracker) instead of hand-rolling ByteTrack, and use `rtmlib` (RTMPose over onnxruntime) instead of installing the full OpenMMLab stack (`mmcv`/`mmdet`/`mmpose`).

**Why:**
- Reimplementing ByteTrack correctly (Kalman filter, cascade matching, track lifecycle) is a research-engineering project on its own — the roadmap already scopes Phase 2 as 6-8 weeks for a reason; spending that budget re-deriving a tracker that ships free with the detector would be the wrong 6-8 weeks.
- The full `mmcv`/`mmdet`/`mmpose` stack is notoriously version-fragile (compiled CUDA ops, tight pinned versions across three packages). `rtmlib` runs the same RTMPose ONNX-exported weights through plain `onnxruntime`, with no compiled-extension version matrix to fight — the practical choice for a small team, not a compromise on the model itself.
- Both choices are swappable later: if RTMW (whole-body, for Indian classical hand detail) or a different tracker outperforms these on the eventual 30-clip eval set, `pipeline/pose.py` and `pipeline/detection.py` are the only two files that would need to change — `pipeline.py`'s orchestration and everything downstream (Phase 3 scoring) doesn't care which library produced the keypoints.
