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

export type IssueType = "angle" | "timing" | "path";

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
