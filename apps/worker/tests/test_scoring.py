"""Tests worker/pipeline/scoring.py, including a synthetic version of
the roadmap's own eval methodology (Phase 3 section): "Bad must score
lower AND the top issue must match the planted error." There's no
real 10-phrase-pair eval set (that needs actual filmed clips per the
roadmap), but the *logic* that would grade one -- does a planted
elbow error get caught and correctly attributed -- can be verified
against a synthetic skeleton with a known, exact ground truth, which
real footage can never give you (you don't actually know the "true"
joint angle in a real video).

Fixture design note, through two failed attempts before this one:

1. First version animated *one* joint (a sine wave) and planted a
   constant offset on it. DTW erased the offset by re-timing to
   whatever other frame in the periodic wave happened to have a
   matching value -- with one varying feature, a constant amplitude
   offset and a phase shift are indistinguishable.
2. Second version animated *three* joints with different sine
   frequencies, thinking that would over-determine the alignment.
   Still failed: within a short clip, DTW could still find a
   partial shift that reduced total cost by spreading a bit of
   mismatch across all three, instead of showing the true error
   cleanly on the planted joint.
3. Third attempt used linear ramps instead of sine waves, on the
   theory that a monotonic signal can't alias. This is actually the
   *worst* choice: for a linear ramp, a constant value-offset and a
   constant time-shift are mathematically interchangeable (shifting
   a ramp by k frames changes its value by slope*k) -- so DTW could
   trade the planted amplitude error for an equivalent time-shift
   almost for free.

What actually works: independent smoothed random walks (cumulative
sum of Gaussian steps) per joint, seeded for reproducibility. Being
uncorrelated frame-to-frame, no shift of a random walk resembles a
constant offset of it, so DTW has no incentive to move off the true
(near-)diagonal, and a planted offset on one joint shows up as a
genuine, isolated value difference. Real dance has this property for
free -- many joints moving in complex, non-redundant patterns; a
synthetic sine or ramp does not, and using one would have silently
overstated how well this actually works.
"""

from __future__ import annotations

import numpy as np

from worker.pipeline.features import (
    L_ANKLE,
    L_ELBOW,
    L_HIP,
    L_KNEE,
    L_SHOULDER,
    L_WRIST,
    R_ANKLE,
    R_ELBOW,
    R_HIP,
    R_KNEE,
    R_SHOULDER,
    R_WRIST,
)
from worker.pipeline.scoring import score_analysis


def _base_pose() -> np.ndarray:
    kp = np.zeros((17, 2))
    kp[L_SHOULDER], kp[R_SHOULDER] = (0.0, -50.0), (20.0, -50.0)
    kp[L_ELBOW], kp[R_ELBOW] = (0.0, -20.0), (20.0, -20.0)
    kp[L_WRIST], kp[R_WRIST] = (0.0, 10.0), (20.0, 10.0)
    kp[L_HIP], kp[R_HIP] = (0.0, 0.0), (20.0, 0.0)
    kp[L_KNEE], kp[R_KNEE] = (0.0, 40.0), (20.0, 40.0)
    kp[L_ANKLE], kp[R_ANKLE] = (0.0, 80.0), (20.0, 80.0)
    return kp


def _set_angle(kp: np.ndarray, a_idx: int, b_idx: int, c_idx: int, angle_deg: float) -> None:
    """Repositions keypoint c_idx (in place) so the angle at b_idx
    between a_idx and c_idx measures exactly angle_deg, preserving the
    original b-c segment length."""

    a, b, c = kp[a_idx], kp[b_idx], kp[c_idx]
    length_bc = float(np.linalg.norm(c - b))
    unit_ba = (a - b) / np.linalg.norm(a - b)
    theta = np.radians(angle_deg)
    rotation = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    kp[c_idx] = b + (rotation @ unit_ba) * length_bc


def _smoothed_random_walk(num_frames: int, scale: float, offset: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return offset + np.cumsum(rng.normal(scale=scale, size=num_frames))


def _animated_sequence(num_frames: int, left_elbow_offset: float = 0.0) -> list[np.ndarray]:
    elbow_signal = _smoothed_random_walk(num_frames, scale=8.0, offset=135.0, seed=1)
    knee_signal = _smoothed_random_walk(num_frames, scale=6.0, offset=150.0, seed=2)
    hip_signal = _smoothed_random_walk(num_frames, scale=5.0, offset=130.0, seed=3)

    frames = []
    for t in range(num_frames):
        kp = _base_pose()
        _set_angle(kp, L_SHOULDER, L_ELBOW, L_WRIST, elbow_signal[t] + left_elbow_offset)
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, knee_signal[t])
        _set_angle(kp, L_SHOULDER, L_HIP, L_KNEE, hip_signal[t])
        frames.append(kp)
    return frames


def test_identical_sequences_score_near_100():
    frames = _animated_sequence(40)
    frame_indices = list(range(40))

    result = score_analysis(frames, frame_indices, 30.0, frames, frame_indices, 30.0)

    assert result.overall_score > 99.0
    for segment in result.segments:
        assert segment.issues == []


def test_planted_elbow_error_is_caught_and_correctly_attributed():
    reference = _animated_sequence(40)
    frame_indices = list(range(40))

    planted_error_deg = 25.0
    bad_user = _animated_sequence(40, left_elbow_offset=planted_error_deg)

    good_result = score_analysis(reference, frame_indices, 30.0, reference, frame_indices, 30.0)
    bad_result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    # 1. bad must score lower
    assert bad_result.overall_score < good_result.overall_score

    # 2. the top issue in every segment must correctly name the planted joint
    assert len(bad_result.segments) > 0
    hits = 0
    for segment in bad_result.segments:
        assert segment.issues, "expected the planted error to surface as an issue"
        top_issue = segment.issues[0]
        if top_issue.joint == "left_elbow":
            hits += 1
    hit_rate = hits / len(bad_result.segments)
    # roadmap's own bar: >= 70% planted-error attribution accuracy
    assert hit_rate >= 0.70, f"only {hit_rate:.0%} of segments correctly attributed the planted error"


def test_planted_error_magnitude_is_recovered_approximately():
    reference = _animated_sequence(40)
    frame_indices = list(range(40))
    planted_error_deg = 25.0
    bad_user = _animated_sequence(40, left_elbow_offset=planted_error_deg)

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    magnitudes = [
        issue.magnitude
        for segment in result.segments
        for issue in segment.issues
        if issue.joint == "left_elbow"
    ]
    assert magnitudes, "expected at least one left_elbow issue"
    assert abs(np.mean(magnitudes) - planted_error_deg) < 3.0


def test_unrelated_joints_are_not_flagged_by_an_elbow_only_error():
    reference = _animated_sequence(40)
    frame_indices = list(range(40))
    bad_user = _animated_sequence(40, left_elbow_offset=25.0)

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    flagged_joints = {issue.joint for segment in result.segments for issue in segment.issues}
    assert "left_knee" not in flagged_joints
    assert "right_elbow" not in flagged_joints
    assert "right_knee" not in flagged_joints
    assert "left_hip" not in flagged_joints


def test_segments_are_ordered_and_cover_the_reference_timeline():
    frames = _animated_sequence(90)  # 3s at 30fps
    frame_indices = list(range(90))

    result = score_analysis(frames, frame_indices, 30.0, frames, frame_indices, 30.0, segment_seconds=1.0)

    assert len(result.segments) >= 2
    for prev, curr in zip(result.segments, result.segments[1:]):
        assert curr.t0 >= prev.t0
    assert result.segments[0].t0 == 0.0


def test_timing_drift_is_detected_when_user_runs_late():
    # 150 identical frames, but "user" is claimed to be recorded at a
    # slower fps than the reference -- so per-frame the values match
    # exactly (DTW aligns on the diagonal, unambiguously optimal since
    # cost is truly zero there), but the *wall-clock* gap between
    # reference-time and user-time grows across the clip. Needs
    # multiple 2s segments (hence 150 frames, not 40) so the drift in
    # a later segment has an earlier segment's baseline to be measured
    # against.
    frames = _animated_sequence(150)
    reference_indices = list(range(150))
    user_indices = list(range(150))

    result = score_analysis(frames, reference_indices, 30.0, frames, user_indices, 20.0)

    timing_issues = [
        issue for segment in result.segments for issue in segment.issues if issue.type == "timing"
    ]
    assert timing_issues, "expected the growing lag from the fps mismatch to be flagged as a timing issue"
    # the drift is monotonically growing, so it should show up as
    # "behind", not "ahead of"
    assert all("behind" in issue.message for issue in timing_issues)


def test_empty_reference_returns_zero_score_without_crashing():
    result = score_analysis([], [], 30.0, [np.zeros((17, 2))], [0], 30.0)
    assert result.overall_score == 0.0
    assert result.segments == []


def test_low_confidence_joint_does_not_produce_a_spurious_issue():
    """Found by comparing real pipeline output against real footage:
    two chest-up-framed clips reported huge hip/knee "errors" that
    were actually just RTMPose guessing at off-screen joints, not real
    technique differences. This is the regression test for the fix
    (features.joint_angles' confidence masking) -- a joint that's
    consistently low-confidence in the user clip shouldn't surface as
    an ANGLE issue even if its raw geometric angle differs a lot from
    the reference. It should instead surface as an OCCLUSION issue --
    that's the whole point of adding that type: turn silent masking
    into a visible, honest signal instead of just hiding the joint."""

    num_frames = 40
    reference = _animated_sequence(num_frames)
    # planted knee error, but the knee is (realistically) low-confidence
    # throughout -- e.g. out of frame
    bad_user = _animated_sequence(num_frames, left_elbow_offset=0.0)
    for kp in bad_user:
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, 40.0)  # wildly different from reference's knee

    frame_indices = list(range(num_frames))
    low_confidence_knee = np.ones(17)
    low_confidence_knee[R_KNEE] = 0.05
    user_scores = [low_confidence_knee.copy() for _ in range(num_frames)]
    reference_scores = [np.ones(17) for _ in range(num_frames)]

    result = score_analysis(
        reference,
        frame_indices,
        30.0,
        bad_user,
        frame_indices,
        30.0,
        reference_scores=reference_scores,
        user_scores=user_scores,
    )

    issues_by_joint_and_type = {
        (issue.joint, issue.type) for segment in result.segments for issue in segment.issues
    }
    assert ("right_knee", "angle") not in issues_by_joint_and_type
    assert ("right_knee", "occlusion") in issues_by_joint_and_type


def _animated_sequence_with_lean(num_frames: int, extra_lean_scale: float = 0.0, extra_lean_seed: int = 20) -> list[np.ndarray]:
    """Like _animated_sequence, plus a horizontal shoulder shift (torso
    lean) that varies over time -- a constant shift would be invisible
    after spine_lean's per-video baseline correction (by design: it's
    meant to ignore a fixed camera angle), so this has to actually
    change over time to be a genuine planted difference."""

    elbow_signal = _smoothed_random_walk(num_frames, scale=8.0, offset=135.0, seed=1)
    knee_signal = _smoothed_random_walk(num_frames, scale=6.0, offset=150.0, seed=2)
    hip_signal = _smoothed_random_walk(num_frames, scale=5.0, offset=130.0, seed=3)
    base_lean = _smoothed_random_walk(num_frames, scale=4.0, offset=0.0, seed=15)
    extra_lean = (
        _smoothed_random_walk(num_frames, scale=extra_lean_scale, offset=0.0, seed=extra_lean_seed)
        if extra_lean_scale
        else np.zeros(num_frames)
    )

    frames = []
    for t in range(num_frames):
        kp = _base_pose()
        shift = base_lean[t] + extra_lean[t]
        # shift shoulders *before* the angle triples that use them as a
        # vertex reference, so the elbow/hip angles land where intended
        # relative to the shifted shoulder, not the original one
        kp[L_SHOULDER] = kp[L_SHOULDER] + np.array([shift, 0.0])
        kp[R_SHOULDER] = kp[R_SHOULDER] + np.array([shift, 0.0])
        _set_angle(kp, L_SHOULDER, L_ELBOW, L_WRIST, elbow_signal[t])
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, knee_signal[t])
        _set_angle(kp, L_SHOULDER, L_HIP, L_KNEE, hip_signal[t])
        frames.append(kp)
    return frames


def test_torso_lean_issue_fires_when_it_genuinely_differs_over_time():
    """spine_lean used to be unconditionally excluded from issues. Now
    that it isn't, this checks it actually fires -- and, implicitly,
    that a *constant* lean offset (the reference's own base_lean walk,
    shared with the user) correctly does NOT fire on its own, since
    only the user's *extra* time-varying lean should show up as a
    genuine difference after baseline correction."""

    num_frames = 40
    reference = _animated_sequence_with_lean(num_frames, extra_lean_scale=0.0)
    bad_user = _animated_sequence_with_lean(num_frames, extra_lean_scale=6.0)
    frame_indices = list(range(num_frames))

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    flagged = {(issue.joint, issue.type) for s in result.segments for issue in s.issues}
    assert ("spine_lean", "angle") in flagged


def _animated_sequence_with_wobble(num_frames: int, extra_wobble_scale: float = 0.0, extra_wobble_seed: int = 40) -> list[np.ndarray]:
    """Like _animated_sequence, plus an extra horizontal drift on the
    left ankle -- shifts the hip-to-ankle (balance_offset) relationship
    over time, independent of the right knee's own animation."""

    elbow_signal = _smoothed_random_walk(num_frames, scale=8.0, offset=135.0, seed=1)
    knee_signal = _smoothed_random_walk(num_frames, scale=6.0, offset=150.0, seed=2)
    hip_signal = _smoothed_random_walk(num_frames, scale=5.0, offset=130.0, seed=3)
    base_wobble = _smoothed_random_walk(num_frames, scale=3.0, offset=0.0, seed=35)
    extra_wobble = (
        _smoothed_random_walk(num_frames, scale=extra_wobble_scale, offset=0.0, seed=extra_wobble_seed)
        if extra_wobble_scale
        else np.zeros(num_frames)
    )

    frames = []
    for t in range(num_frames):
        kp = _base_pose()
        _set_angle(kp, L_SHOULDER, L_ELBOW, L_WRIST, elbow_signal[t])
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, knee_signal[t])
        _set_angle(kp, L_SHOULDER, L_HIP, L_KNEE, hip_signal[t])
        kp[L_ANKLE] = kp[L_ANKLE] + np.array([base_wobble[t] + extra_wobble[t], 0.0])
        frames.append(kp)
    return frames


def test_balance_issue_fires_when_wobble_exceeds_the_reference():
    num_frames = 40
    reference = _animated_sequence_with_wobble(num_frames, extra_wobble_scale=0.0)
    # note: shifting the left ankle (to plant a balance difference) also
    # perturbs the measured left_knee angle, since the ankle keypoint is
    # shared between the two features -- same adjacent-keypoint leakage
    # documented in scripts/eval_planted_errors.py. This test only
    # checks that a "balance" issue appears among the flagged types, not
    # that it's the *only* one, so that leakage doesn't invalidate it.
    bad_user = _animated_sequence_with_wobble(num_frames, extra_wobble_scale=9.0)
    frame_indices = list(range(num_frames))

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    flagged_types = {issue.type for s in result.segments for issue in s.issues}
    assert "balance" in flagged_types


def test_balance_issue_is_suppressed_when_the_ankles_are_too_low_confidence_to_trust():
    # Same wobble that fires in the test above -- but here the user's
    # ankles are barely visible (confidence 0.1, under the 0.3 bar) for
    # the whole clip, as on real footage framed above the feet. A balance
    # "wobble" measured from those guesses is noise, so nothing is said.
    num_frames = 40
    reference = _animated_sequence_with_wobble(num_frames, extra_wobble_scale=0.0)
    bad_user = _animated_sequence_with_wobble(num_frames, extra_wobble_scale=9.0)
    frame_indices = list(range(num_frames))

    confident = [np.full(17, 0.9) for _ in range(num_frames)]
    unsure_ankles = []
    for _ in range(num_frames):
        s = np.full(17, 0.9)
        s[[L_ANKLE, R_ANKLE]] = 0.1
        unsure_ankles.append(s)

    with_visible_ankles = score_analysis(
        reference, frame_indices, 30.0, bad_user, frame_indices, 30.0,
        reference_scores=confident, user_scores=confident,
    )
    with_hidden_ankles = score_analysis(
        reference, frame_indices, 30.0, bad_user, frame_indices, 30.0,
        reference_scores=confident, user_scores=unsure_ankles,
    )

    assert "balance" in _issue_types(with_visible_ankles)
    assert "balance" not in _issue_types(with_hidden_ankles)


def _dampened_animated_sequence(num_frames: int, damp: float) -> list[np.ndarray]:
    """Like _animated_sequence, but the fluctuation *amplitude* of every
    signal is scaled by `damp` around the same mean -- damp=1.0 is
    identical to _animated_sequence; damp<1 moves much less without
    changing the average pose much, which is what "low energy" should
    detect (as distinct from "wrong angle")."""

    elbow_signal = _smoothed_random_walk(num_frames, scale=8.0, offset=135.0, seed=1)
    knee_signal = _smoothed_random_walk(num_frames, scale=6.0, offset=150.0, seed=2)
    hip_signal = _smoothed_random_walk(num_frames, scale=5.0, offset=130.0, seed=3)
    elbow_signal = 135.0 + (elbow_signal - 135.0) * damp
    knee_signal = 150.0 + (knee_signal - 150.0) * damp
    hip_signal = 130.0 + (hip_signal - 130.0) * damp

    frames = []
    for t in range(num_frames):
        kp = _base_pose()
        _set_angle(kp, L_SHOULDER, L_ELBOW, L_WRIST, elbow_signal[t])
        _set_angle(kp, R_HIP, R_KNEE, R_ANKLE, knee_signal[t])
        _set_angle(kp, L_SHOULDER, L_HIP, L_KNEE, hip_signal[t])
        frames.append(kp)
    return frames


def test_energy_issue_fires_when_user_moves_much_less_than_reference():
    num_frames = 60
    reference = _dampened_animated_sequence(num_frames, damp=1.0)
    bad_user = _dampened_animated_sequence(num_frames, damp=0.15)
    frame_indices = list(range(num_frames))

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    flagged_types = {issue.type for s in result.segments for issue in s.issues}
    assert "energy" in flagged_types


def test_energy_issue_does_not_fire_when_reference_itself_is_still():
    # both sides nearly frozen -- there's no real reference motion to
    # be "missing", so this must not fire (see MIN_REFERENCE_ENERGY_DEG)
    num_frames = 40
    reference = _dampened_animated_sequence(num_frames, damp=0.02)
    bad_user = _dampened_animated_sequence(num_frames, damp=0.02)
    frame_indices = list(range(num_frames))

    result = score_analysis(reference, frame_indices, 30.0, bad_user, frame_indices, 30.0)

    flagged_types = {issue.type for s in result.segments for issue in s.issues}
    assert "energy" not in flagged_types


def _issue_types(result) -> set[str]:
    return {issue.type for segment in result.segments for issue in segment.issues}


def test_same_motion_at_different_frame_rates_raises_no_tempo_or_energy_issue_reference_faster():
    # Regression: the first real-footage run (a ~60 fps reference vs. a
    # ~30 fps user clip) flagged "tempo" in every window, because the span
    # check compared raw frame counts instead of seconds. The dancer here
    # does *exactly* the same motion at the same real-world speed -- only
    # the recording frame rate differs -- so neither tempo nor energy
    # (also frame-rate-sensitive, in the other direction) should fire.
    fast = _animated_sequence(120)  # 2s at 60fps
    slow = fast[::2]  # the same 2s of motion, sampled at 30fps

    result = score_analysis(fast, list(range(120)), 60.0, slow, list(range(60)), 30.0)

    assert "tempo" not in _issue_types(result)
    assert "energy" not in _issue_types(result)


def test_same_motion_at_different_frame_rates_raises_no_tempo_or_energy_issue_user_faster():
    fast = _animated_sequence(120)
    slow = fast[::2]

    result = score_analysis(slow, list(range(60)), 30.0, fast, list(range(120)), 60.0)

    assert "tempo" not in _issue_types(result)
    assert "energy" not in _issue_types(result)


def test_tempo_issue_flags_a_likely_skipped_move():
    reference = _animated_sequence(60)  # 2s at 30fps
    bad_user = reference[0:20] + reference[40:60]  # the middle 20 frames are missing entirely

    result = score_analysis(
        reference, list(range(60)), 30.0, bad_user, list(range(len(bad_user))), 30.0, segment_seconds=0.5
    )

    tempo_issues = [issue for s in result.segments for issue in s.issues if issue.type == "tempo"]
    assert tempo_issues, "expected at least one tempo issue for the skipped chunk"
    assert any("skipped" in issue.message for issue in tempo_issues)


def test_tempo_issue_flags_a_likely_added_move():
    reference = _animated_sequence(40)
    # frames 10-19 are repeated, as if the dancer added or repeated a move
    bad_user = reference[0:10] + reference[10:20] + reference[10:20] + reference[20:40]

    result = score_analysis(
        reference, list(range(40)), 30.0, bad_user, list(range(len(bad_user))), 30.0, segment_seconds=0.5
    )

    tempo_issues = [issue for s in result.segments for issue in s.issues if issue.type == "tempo"]
    assert tempo_issues, "expected at least one tempo issue for the repeated chunk"
    assert any("added or repeated" in issue.message for issue in tempo_issues)
