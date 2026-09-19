#!/usr/bin/env python
"""Planted-signal eval for the tempo / energy / occlusion issue types, on a
REAL pose sequence.

eval_planted_errors.py checks that a planted *joint-angle* error is
attributed to the right joint. This does the same for the window-level
issue types added later, which had only ever been tested against a
synthetic skeleton -- and whose first run on real footage turned up three
false-positive bugs (see apps/worker/README.md). It takes a real extracted
sequence as the "reference", derives a "user" from it with ONE known change
planted, and checks the right issue shows up in the right windows (and not
in windows far from the change).

Planted changes (ground truth is exact because the user *is* the
reference, edited):
  skip      a chunk of frames removed        -> expect `tempo` "skipped"
  repeat    a chunk of frames duplicated     -> expect `tempo` "added"
  damp      motion shrunk toward the mean    -> expect `energy`
  mask      a wrist's confidence set to ~0   -> expect `occlusion` on right_elbow

Every variant runs at two frame-rate configurations: user at the same fps
as the reference, and user at half the fps (every 2nd frame) -- the
mismatch that produced the original false positives.

NOT covered: `balance`. It needs the ankles visible, and on the clips
available here they clear the confidence bar in only ~30-60% of frames, so
the new visibility gate correctly suppresses it -- there is no real footage
here to test it on. That needs a full-body clip.

Bars (fixed before running): >= 70% detection over the variants the design
should be able to catch (roadmap's own bar). Variants below the design's own
detection floor are included and reported but not counted -- they show where
sensitivity actually ends. False-positive rates are reported, with no bar.

    python scripts/eval_planted_signals.py --keypoints clip_keypoints.npz [more.npz ...]
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np

from worker.pipeline.features import R_WRIST, feature_sequence
from worker.pipeline.scoring import _segment_energy, score_analysis

DETECTION_TARGET = 0.70
TOLERANCE_S = 1.0  # a flagged window within this of the edit still counts as "near" it
FP_MARGIN_S = 2.0  # a window entirely this far from the edit is "far" -- flags there are false positives


@dataclass
class Case:
    category: str
    name: str
    expected: bool  # should the design be able to catch this?
    detected: bool
    false_positive_windows: int
    far_windows: int


def _windows(result):
    return [(s.t0, s.t1, s.issues) for s in result.segments]


def _score(ref, user, user_fps_divisor):
    kp, sc, fi, fps = ref
    ukp, usc = user
    if user_fps_divisor > 1:
        ukp, usc = ukp[::user_fps_divisor], usc[::user_fps_divisor]
    return score_analysis(
        list(kp), list(fi), fps,
        list(ukp), list(range(len(ukp))), fps / user_fps_divisor,
        reference_scores=list(sc), user_scores=list(usc),
    )


def _overlaps(t0, t1, a, b):
    return t1 >= a and t0 <= b


def _tempo_case(ref, kind, start_s, dur_s, divisor):
    kp, sc, fi, fps = ref
    i0 = int(round(start_s * fps))
    n = int(round(dur_s * fps))
    if kind == "skip":
        ukp = np.concatenate([kp[:i0], kp[i0 + n:]])
        usc = np.concatenate([sc[:i0], sc[i0 + n:]])
        keyword = "skipped"
    else:
        ukp = np.concatenate([kp[: i0 + n], kp[i0 : i0 + n], kp[i0 + n:]])
        usc = np.concatenate([sc[: i0 + n], sc[i0 : i0 + n], sc[i0 + n:]])
        keyword = "added"

    result = _score(ref, (ukp, usc), divisor)
    lo, hi = fi[i0] / fps, fi[min(i0 + n, len(fi) - 1)] / fps
    detected, fp, far = False, 0, 0
    for t0, t1, issues in _windows(result):
        tempo = [i for i in issues if i.type == "tempo"]
        if _overlaps(t0, t1, lo - TOLERANCE_S, hi + TOLERANCE_S):
            detected = detected or any(keyword in i.message for i in tempo)
        elif t1 < lo - FP_MARGIN_S or t0 > hi + FP_MARGIN_S:
            far += 1
            fp += 1 if tempo else 0
    return detected, fp, far


def _damped(ref, damp):
    kp = ref[0]
    mean = kp.mean(axis=0)
    return mean + damp * (kp - mean)


def _measured_energy_ratio(ref, damp):
    """Ground truth for the energy case. Shrinking *keypoint* motion by
    `damp` does NOT shrink *joint-angle* motion by `damp` (angles aren't
    linear in keypoint position -- x0.4 gave a ratio of ~0.6, not 0.4, on
    the real clips), so the planted change is labelled by the ratio it
    actually produces, measured with the same function scoring uses."""

    kp, sc, fi, fps = ref
    idx = list(range(len(kp)))
    base = _segment_energy(feature_sequence(list(kp), list(sc)), idx, fps)
    damped = _segment_energy(feature_sequence(list(_damped(ref, damp)), list(sc)), idx, fps)
    return damped / base


def _energy_case(ref, damp, divisor):
    kp, sc, fi, fps = ref
    result = _score(ref, (_damped(ref, damp), sc), divisor)
    windows = _windows(result)
    flagged = sum(1 for _, _, issues in windows if any(i.type == "energy" for i in issues))
    return flagged, len(windows)


def _mask_case(ref, start_s, end_s, divisor):
    kp, sc, fi, fps = ref
    usc = sc.copy()
    usc[int(round(start_s * fps)) : int(round(end_s * fps)), R_WRIST] = 0.05
    result = _score(ref, (kp, usc), divisor)
    inside_hit = inside = outside_flag = outside = 0
    for t0, t1, issues in _windows(result):
        occ = any(i.type == "occlusion" and i.joint == "right_elbow" for i in issues)
        if t0 >= start_s and t1 <= end_s:
            inside += 1
            inside_hit += occ
        elif t1 <= start_s or t0 >= end_s:
            outside += 1
            outside_flag += occ
    return inside_hit, inside, outside_flag, outside


def run(npz_path: Path) -> list[Case]:
    data = np.load(npz_path)
    ref = (data["keypoints"], data["scores"], list(data["frame_indices"]), float(data["fps"]))
    duration = len(ref[0]) / ref[3]
    print(f"\n=== {npz_path.name}: {len(ref[0])} frames, {ref[3]:.1f} fps, {duration:.1f}s ===")
    cases: list[Case] = []

    # Control: an unedited copy should raise none of the window-level types
    # (occlusion legitimately fires here on real low-confidence knees, so it
    # isn't part of the control).
    for divisor in (1, 2):
        result = _score(ref, (ref[0], ref[1]), divisor)
        bad = {i.type for _, _, iss in _windows(result) for i in iss} & {"tempo", "energy", "balance"}
        label = f"control (unedited, user fps /{divisor})"
        print(f"  {label:<44} tempo/energy/balance raised: {sorted(bad) or 'none'}")
        cases.append(Case("control", label, True, not bad, len(bad), 1))

    # (design detects a skip only if it empties >~0.8s of a 2s window, and a
    # repeat only if it adds >~1.2s -- shorter edits are below the design's
    # own floor, kept to show where sensitivity ends)
    for kind, durations in (("skip", [(0.6, False), (1.2, True), (2.0, True)]),
                            ("repeat", [(0.8, False), (1.6, True), (2.4, True)])):
        for frac in (0.25, 0.5, 0.75):
            for dur, expected in durations:
                start = duration * frac
                if start + dur >= duration - 0.5:
                    continue
                for divisor in (1, 2):
                    det, fp, far = _tempo_case(ref, kind, start, dur, divisor)
                    name = f"{kind} {dur:.1f}s @ {frac:.0%}, user fps /{divisor}"
                    print(f"  {name:<44} expected={str(expected):<5} detected={det!s:<5} far-window tempo flags={fp}/{far}")
                    cases.append(Case("tempo", name, expected, det, fp, far))

    # Energy threshold is a 0.5 ratio: clearly below (<=0.4) should be
    # flagged, clearly above (>=0.6) should not; in between is a boundary
    # case -- reported, not counted either way.
    for damp in (0.1, 0.15, 0.25, 0.4, 0.7):
        ratio = _measured_energy_ratio(ref, damp)
        if ratio <= 0.4:
            expected, counted = True, True
        elif ratio >= 0.6:
            expected, counted = False, True
        else:
            expected, counted = False, False
        for divisor in (1, 2):
            flagged, total = _energy_case(ref, damp, divisor)
            name = f"damp x{damp} (energy ratio {ratio:.2f}), fps /{divisor}"
            det = flagged >= max(1, total // 2)
            tag = "boundary" if not counted else f"expected={expected}"
            print(f"  {name:<50} {tag:<15} energy flagged in {flagged}/{total} windows")
            if counted:
                cases.append(Case("energy", name, expected, det, 0, total))

    # Mask the wrist from the start so at least two whole windows lie
    # inside the masked span and at least one lies clearly outside it.
    for divisor in (1, 2):
        start, end = 0.0, duration * 0.62
        hit, inside, fp, outside = _mask_case(ref, start, end, divisor)
        name = f"mask right wrist {start:.1f}-{end:.1f}s, user fps /{divisor}"
        print(f"  {name:<44} occlusion(right_elbow) in {hit}/{inside} inside windows, {fp}/{outside} outside")
        cases.append(Case("occlusion", name, True, inside > 0 and hit / inside >= DETECTION_TARGET, fp, outside))
    return cases


def summarize(cases: list[Case]) -> None:
    print("\n=== summary (all clips) ===")
    for category in ("control", "tempo", "energy", "occlusion"):
        group = [c for c in cases if c.category == category]
        expected = [c for c in group if c.expected]
        hits = sum(c.detected for c in expected)
        fp = sum(c.false_positive_windows for c in group)
        far = sum(c.far_windows for c in group)
        rate = hits / len(expected) if expected else 0.0
        status = "PASS" if rate >= DETECTION_TARGET else "FAIL"
        below = [c for c in group if not c.expected]
        below_hits = sum(c.detected for c in below)
        line = f"{category:<10} detection {hits}/{len(expected)} = {rate:.0%} [{status}]"
        if category != "control":
            line += f" | false-positive windows {fp}/{far}"
        if below:
            line += f" | below-design-floor variants that were flagged anyway: {below_hits}/{len(below)}"
        print(line)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keypoints", type=Path, nargs="+", required=True)
    args = parser.parse_args()
    all_cases: list[Case] = []
    for path in args.keypoints:
        all_cases.extend(run(path))
    summarize(all_cases)
