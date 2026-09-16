/**
 * The canonical AnalysisResult contract.
 *
 * Frontend, API, worker, and Figma all speak this shape. If a field is not
 * here, it does not exist in the product — no page may invent its own
 * metric (e.g. `pose_accuracy = similarity + 3`).
 *
 * Mirrors packages/schema/python/cadence_schema/analysis_result.py
 * field-for-field. Keep the two in sync by hand until a codegen step
 * replaces this note.
 */

export type AnalysisStatus =
  | "queued"
  | "running"
  | "needs_dancer_pick"
  | "complete"
  | "rejected";

// "angle": a joint's angle differs from the reference (arm/leg joints alike -- the
//   `joint` field, e.g. "left_elbow" vs "right_knee", distinguishes arm from leg;
//   there's no separate arm/leg type).
// "timing": reference/user time gap is growing (independent of score).
// "path": spatial trajectory deviation -- reserved, not generated yet.
// "occlusion": a joint was too low-confidence to score for part of this window.
// "tempo": local DTW stretch/compression -- a move happened notably faster/slower,
//   or was likely skipped/added, vs the reference.
// "energy": overall movement magnitude in this window is well below the reference.
// "balance": hip position wanders from the base of support more than the reference.
export type IssueType =
  | "angle"
  | "timing"
  | "path"
  | "occlusion"
  | "tempo"
  | "energy"
  | "balance";

export interface TrackingInfo {
  confidence: number; // 0..1
  reliable_frame_pct: number; // 0..100
  person_count: number;
  lock_id: string | null;
}

export interface OverallScore {
  score: number; // 0..100
  method: string;
  version: string;
}

export interface Issue {
  joint: string;
  type: IssueType;
  magnitude: number;
  message: string;
}

export interface Segment {
  t0: number;
  t1: number;
  score: number; // 0..100
  issues: Issue[];
  confidence: number; // 0..1
}

export interface Artifacts {
  overlay_url: string | null;
  skeleton_3d_url: string | null;
  thumbs: string[];
}

export interface QualityGate {
  passed: boolean;
  reasons: string[];
}

export interface AnalysisResult {
  analysis_id: string;
  user_id: string;
  status: AnalysisStatus;
  tracking: TrackingInfo;
  overall: OverallScore | null;
  segments: Segment[];
  artifacts: Artifacts;
  quality_gate: QualityGate;
}
