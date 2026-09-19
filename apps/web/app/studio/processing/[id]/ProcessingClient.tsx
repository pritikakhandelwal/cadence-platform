"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Logo } from "@/components/Logo";
import { getAnalysis, ApiError } from "@/lib/api";

const POLL_INTERVAL_MS = 2500;

export function ProcessingClient({ id }: { id: string }) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const redirected = useRef(false);

  useEffect(() => {
    let cancelled = false;

    async function poll() {
      try {
        const result = await getAnalysis(id);
        if (cancelled || redirected.current) return;

        if (result.status === "needs_dancer_pick") {
          redirected.current = true;
          router.replace(`/studio/pick/${id}`);
        } else if (result.status === "complete") {
          redirected.current = true;
          router.replace(`/studio/results/${id}`);
        } else if (result.status === "rejected") {
          redirected.current = true;
          const reason = result.quality_gate.reasons[0] ?? "This video couldn't be analyzed.";
          router.replace(`/studio/upload?rejected=${encodeURIComponent(reason)}`);
        }
        // queued / running: keep polling
      } catch (err) {
        if (cancelled) return;
        if (err instanceof ApiError && err.status === 401) {
          redirected.current = true;
          router.replace(`/login?next=/studio/processing/${id}`);
          return;
        }
        setError(err instanceof ApiError ? err.message : "Lost connection while checking on this analysis.");
      }
    }

    poll();
    const interval = setInterval(poll, POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [id, router]);

  return (
    <div className="flex flex-col min-h-screen">
      <header className="px-5 md:px-16 py-5 md:py-6">
        <Logo />
      </header>
      <div className="flex-grow flex flex-col items-center justify-center gap-[26px] cadence-dotgrid">
        <div className="relative flex items-center justify-center" style={{ width: 150, height: 150 }}>
          <div
            className="cadence-ring absolute inset-0 rounded-full"
            style={{ border: "1.5px solid var(--accent)" }}
          />
          <div
            className="cadence-ring cadence-ring-delay absolute rounded-full"
            style={{ inset: 22, border: "1.5px solid var(--sky)" }}
          />
          <svg className="cadence-spark" width="26" height="26" viewBox="0 0 24 24" fill="var(--accent)">
            <path d="M12 2l1.8 6.4L20 10l-6.2 1.6L12 18l-1.8-6.4L4 10l6.2-1.6L12 2z" />
          </svg>
        </div>
        <div className="font-serif bg-page px-4 py-1 rounded-lg" style={{ fontSize: 24, fontWeight: 500 }}>
          Analyzing your performance
        </div>
        {error ? (
          <div className="text-sm text-[#B0453D] bg-page px-4 py-0.5 rounded-lg">{error}</div>
        ) : (
          <div className="text-sm text-muted bg-page px-4 py-0.5 rounded-lg">This usually takes under a minute.</div>
        )}
        <a
          href="/studio/upload"
          className="mt-2.5 text-[13px] text-muted underline bg-page px-3 py-0.5 rounded-lg"
        >
          Cancel
        </a>
      </div>
    </div>
  );
}
