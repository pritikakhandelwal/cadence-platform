import type { AnalysisResult, AnalysisStatus, Segment } from "@cadence/schema";

export function makeAnalysis(
  status: AnalysisStatus,
  overrides: Partial<AnalysisResult> = {}
): AnalysisResult {
  return {
    analysis_id: "abc",
    user_id: "u1",
    status,
    tracking: { confidence: 0, reliable_frame_pct: 0, person_count: 0, lock_id: null },
    overall: null,
    segments: [],
    artifacts: { overlay_url: null, skeleton_3d_url: null, thumbs: [] },
    quality_gate: { passed: false, reasons: [] },
    ...overrides,
  };
}

export function makeCompleteAnalysis(segments: Segment[]): AnalysisResult {
  return makeAnalysis("complete", {
    tracking: { confidence: 0.9, reliable_frame_pct: 100, person_count: 2, lock_id: "1" },
    overall: { score: 38.6458, method: "angle-dtw-v2", version: "2" },
    segments,
    quality_gate: { passed: true, reasons: [] },
  });
}
