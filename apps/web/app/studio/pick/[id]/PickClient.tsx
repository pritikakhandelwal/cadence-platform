"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { StudioHeader } from "@/components/StudioHeader";
import { Button } from "@/components/Button";
import { getCandidateTracks, lockTrack, ApiError, type CandidateTrack } from "@/lib/api";

export function PickClient({ id }: { id: string }) {
  const router = useRouter();
  const [tracks, setTracks] = useState<CandidateTrack[] | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    getCandidateTracks(id)
      .then(setTracks)
      .catch((err) => {
        if (err instanceof ApiError && err.status === 401) {
          router.replace(`/login?next=/studio/pick/${id}`);
          return;
        }
        setError(err instanceof ApiError ? err.message : "Couldn't load the candidates for this analysis.");
      });
  }, [id, router]);

  async function handleContinue() {
    if (selected === null) return;
    setPending(true);
    setError(null);
    try {
      await lockTrack(id, selected);
      router.push(`/studio/processing/${id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Couldn't lock onto that person. Try again.");
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      <StudioHeader step={2} />

      <div className="flex-grow flex flex-col items-center justify-center px-5 md:px-16 py-6 md:py-8 gap-[30px]">
        <div className="text-center max-w-[560px] flex flex-col gap-1.5">
          <h1 className="font-serif" style={{ fontSize: 26, fontWeight: 500 }}>
            Which one is you?
          </h1>
          <p className="text-sm text-muted">We spotted more than one person. Pick your preview below.</p>
        </div>

        {error && <div className="text-sm text-[#B0453D]">{error}</div>}

        {!tracks && !error && <div className="text-sm text-muted">Loading candidates...</div>}

        {tracks && (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6 w-full max-w-[1180px]">
            {tracks.map((track) => {
              const isSelected = selected === track.track_id;
              return (
                <button
                  key={track.track_id}
                  type="button"
                  onClick={() => setSelected(track.track_id)}
                  className="text-left rounded-2xl overflow-hidden flex flex-col"
                  style={{
                    border: `2px solid ${isSelected ? "var(--accent)" : "var(--border)"}`,
                    background: isSelected ? "var(--accent-tint)" : "#FFFFFF",
                  }}
                >
                  <div className="relative" style={{ height: 240, background: "#171522" }}>
                    <video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" />
                    <div
                      className="absolute top-2.5 right-2.5 rounded-full flex items-center justify-center"
                      style={{
                        width: 26,
                        height: 26,
                        background: isSelected ? "var(--accent)" : "rgba(255,255,255,0.22)",
                      }}
                    >
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#FFFFFF" strokeWidth="2.4">
                        <path d="M4 12l5 5L20 6" strokeLinecap="round" strokeLinejoin="round" />
                      </svg>
                    </div>
                  </div>
                  <div className="px-[18px] py-3.5 flex items-center gap-2">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.8">
                      <circle cx="12" cy="8" r="3.5" />
                      <path d="M5 20c0-4 3-6.5 7-6.5s7 2.5 7 6.5" strokeLinecap="round" />
                    </svg>
                    <div className="text-[15px] font-semibold">Person {track.track_id}</div>
                  </div>
                </button>
              );
            })}
          </div>
        )}

        <p className="text-sm text-muted text-center">
          Not seeing a clear preview?{" "}
          <Link href="/studio/upload" className="text-accent font-semibold no-underline">
            Try a different video.
          </Link>
        </p>
      </div>

      <footer className="flex justify-end px-5 md:px-16 py-5 border-t border-border">
        <Button onClick={handleContinue} disabled={selected === null || pending}>
          {pending ? "Locking in..." : "Continue"}
        </Button>
      </footer>
    </div>
  );
}
