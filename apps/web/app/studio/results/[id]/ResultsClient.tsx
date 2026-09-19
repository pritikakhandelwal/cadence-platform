"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import type { AnalysisResult, Issue } from "@cadence/schema";
import { Logo } from "@/components/Logo";
import { LinkButton } from "@/components/Button";
import { ScoreGauge } from "@/components/ScoreGauge";
import { VideoToggle, type VideoView } from "@/components/VideoToggle";
import { ISSUE_TYPES } from "@/lib/issueTypes";
import { getAnalysis, ApiError } from "@/lib/api";

function formatTime(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}:${s.toString().padStart(2, "0")}`;
}

interface TimelineMarker {
  key: string;
  t0: number;
  issue: Issue;
}

export function ResultsClient({ id }: { id: string }) {
  const router = useRouter();
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<VideoView>("mine");

  useEffect(() => {
    getAnalysis(id)
      .then(setResult)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.replace(`/login?next=/studio/results/${id}`);
          return;
        }
        setError(err instanceof ApiError ? err.message : "Couldn't load this analysis.");
      });
  }, [id, router]);

  if (error) {
    return (
      <div className="flex flex-col min-h-screen items-center justify-center gap-4">
        <div className="text-sm text-[#B0453D]">{error}</div>
        <LinkButton href="/studio/upload" variant="outline">
          Start a new analysis
        </LinkButton>
      </div>
    );
  }

  if (!result) {
    return <div className="flex-grow flex items-center justify-center text-muted text-sm min-h-screen">Loading...</div>;
  }

  if (result.status !== "complete") {
    return (
      <div className="flex flex-col min-h-screen items-center justify-center gap-4 text-center px-6">
        <div className="text-sm text-muted max-w-sm">
          This analysis isn&apos;t finished yet ({result.status}).{" "}
          {result.quality_gate.reasons[0]}
        </div>
        <LinkButton href={`/studio/processing/${id}`} variant="outline">
          Back to processing
        </LinkButton>
      </div>
    );
  }

  const markers: TimelineMarker[] = result.segments.flatMap((segment) =>
    segment.issues.map((issue, i) => ({
      key: `${segment.t0}-${i}`,
      t0: segment.t0,
      issue,
    }))
  );
  const totalDuration = result.segments.at(-1)?.t1 ?? 1;

  const confidencePct = Math.round(result.tracking.confidence * 100);
  const reliablePct = Math.round(result.tracking.reliable_frame_pct);

  return (
    <div className="flex flex-col min-h-screen">
      <header className="flex items-center justify-between px-16 py-6 border-b border-border">
        <Logo />
        <LinkButton href="/studio/upload" variant="outline" className="!px-5 !py-2.5">
          Analyze another video
        </LinkButton>
      </header>

      <div className="px-16 pt-8 pb-7 flex flex-col gap-[22px]">
        <div className="bg-white border border-border rounded-[20px] px-9 py-7 flex gap-11 items-center">
          <ScoreGauge score={result.overall?.score ?? null} />
          <div className="flex flex-col gap-2">
            <div className="text-[13px] font-semibold uppercase text-accent" style={{ letterSpacing: "0.06em" }}>
              Overall score
            </div>
            <h1 className="font-serif" style={{ fontSize: 24, fontWeight: 500 }}>
              {result.overall ? `${result.overall.method} · v${result.overall.version}` : "Your result appears here"}
            </h1>
            <div className="flex gap-8 mt-1.5">
              <div>
                <div className="text-[13px] text-muted">Tracking confidence</div>
                <div className="text-lg font-semibold">{result.tracking.confidence ? `${confidencePct}%` : "—"}</div>
              </div>
              <div>
                <div className="text-[13px] text-muted">Reliable frames</div>
                <div className="text-lg font-semibold">{result.tracking.reliable_frame_pct ? `${reliablePct}%` : "—"}</div>
              </div>
              <div>
                <div className="text-[13px] text-muted">People in frame</div>
                <div className="text-lg font-semibold">{result.tracking.person_count || "—"}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="bg-white border border-border rounded-[20px] px-9 py-[26px] flex flex-col gap-[18px]">
          <div className="flex items-center justify-between">
            <h2 className="font-serif" style={{ fontSize: 20, fontWeight: 500 }}>
              Video comparison
            </h2>
            <VideoToggle value={view} onChange={setView} />
          </div>
          <div className="relative rounded-2xl overflow-hidden" style={{ height: 340, background: "#171522" }}>
            <video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" />
            <div className="absolute top-4 left-4 bg-white/15 text-white text-xs px-3.5 py-1.5 rounded-full">
              {view === "mine" ? "Your video" : "Reference video"}
            </div>
          </div>
        </div>

        {markers.length > 0 ? (
          <div className="bg-white border border-border rounded-[20px] px-9 py-[26px] flex flex-col gap-5">
            <h2 className="font-serif" style={{ fontSize: 20, fontWeight: 500 }}>
              Timeline
            </h2>

            <div className="flex gap-5 text-xs text-muted flex-wrap">
              {Object.entries(ISSUE_TYPES).map(([type, info]) => (
                <div key={type} className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full inline-block" style={{ background: info.color }} />
                  {info.label}
                </div>
              ))}
            </div>

            <div className="relative h-2 rounded-full" style={{ background: "#EDE7F9", margin: "8px 9px 0" }}>
              {markers.map((marker) => (
                <div
                  key={marker.key}
                  className="absolute rounded-full border-[3px] border-white"
                  style={{
                    top: -5,
                    width: 18,
                    height: 18,
                    left: `${(marker.t0 / totalDuration) * 100}%`,
                    background: ISSUE_TYPES[marker.issue.type].color,
                    transform: "translateX(-50%)",
                  }}
                />
              ))}
            </div>

            <div className="flex flex-col gap-2.5 mt-1">
              {markers.map((marker) => {
                const info = ISSUE_TYPES[marker.issue.type];
                return (
                  <div
                    key={marker.key}
                    className="flex items-start gap-4 px-[18px] py-3.5 border rounded-xl"
                    style={{ borderColor: "#EDE7F9" }}
                  >
                    <div className="font-serif text-sm text-muted w-[50px] flex-shrink-0">{formatTime(marker.t0)}</div>
                    <div
                      className="text-xs font-semibold px-3 py-1 rounded-full flex-shrink-0 whitespace-nowrap"
                      style={{ background: `${info.color}1A`, color: info.color }}
                    >
                      {info.label}
                    </div>
                    <div className="text-sm leading-relaxed">{marker.issue.message}</div>
                  </div>
                );
              })}
            </div>
          </div>
        ) : (
          <div className="bg-white border border-border rounded-[20px] px-9 py-[30px] flex flex-col gap-5">
            <div className="text-center flex flex-col gap-1">
              <h2 className="font-serif" style={{ fontSize: 20, fontWeight: 500 }}>
                What Cadence looks for
              </h2>
              <p className="text-[13px] text-muted">No issues were flagged for this run -- here&apos;s what gets tagged when there are.</p>
            </div>
            <div className="grid grid-cols-3 gap-5">
              {Object.entries(ISSUE_TYPES)
                .filter(([type]) => type !== "path")
                .map(([type, info]) => (
                  <div key={type} className="flex items-center gap-3 px-4 py-3.5 border rounded-2xl" style={{ borderColor: "#EDE7F9" }}>
                    <div
                      className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                      style={{ background: `${info.color}1A` }}
                    >
                      {info.icon}
                    </div>
                    <div>
                      <div className="text-sm font-semibold">{info.label}</div>
                      <div className="text-xs text-muted">{info.caption}</div>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
