# @cadence/schema

The frozen `AnalysisResult` contract — the one object every layer of Cadence (API, worker, web, Figma) speaks. See [ROADMAP.md § 4](../../ROADMAP.md#4-canonical-analysisresult-build-this-first) for the rationale.

- [`python/cadence_schema/analysis_result.py`](python/cadence_schema/analysis_result.py) — Pydantic models, used by `apps/api` and `apps/worker`.
- [`typescript/src/analysisResult.ts`](typescript/src/analysisResult.ts) — TypeScript types, used by `apps/web`.

The two are hand-mirrored field-for-field. If you change one, change the other in the same commit — CI checks both build/typecheck but does not yet diff them for drift (add that if it becomes a real problem).

## Rule

If a field isn't in this contract, it doesn't exist in the product. No page, endpoint, or worker may invent an ad hoc metric outside this shape.
