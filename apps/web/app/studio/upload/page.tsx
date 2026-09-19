"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { StudioHeader } from "@/components/StudioHeader";
import { Button } from "@/components/Button";
import { IconBadge } from "@/components/IconBadge";
import { Toast } from "@/components/Toast";
import { me, createAnalysis, ApiError } from "@/lib/api";

type RefMode = "upload" | "link";

function Dropzone({
  file,
  onChange,
  height,
}: {
  file: File | null;
  onChange: (file: File | null) => void;
  height: number;
}) {
  return (
    <label
      className="border-[1.5px] border-dashed rounded-2xl flex flex-col items-center justify-center gap-2.5 cursor-pointer bg-white"
      style={{ height, borderColor: "#C4B8EE" }}
    >
      <input
        type="file"
        accept="video/mp4"
        className="hidden"
        onChange={(e) => onChange(e.target.files?.[0] ?? null)}
      />
      <IconBadge size={file ? 48 : 56}>
        <svg width={file ? 20 : 24} height={file ? 20 : 24} viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
          <path d="M12 15V3m0 0l-4 4m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </IconBadge>
      <div className="text-[15px] font-semibold">
        {file ? file.name : "Drag & drop, or click to upload"}
      </div>
      {!file && <div className="text-[13px] text-muted">MP4, up to 250MB</div>}
    </label>
  );
}

function UploadForm() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [checkingAuth, setCheckingAuth] = useState(true);
  const [rejected, setRejected] = useState(searchParams.get("rejected"));
  const [userVideo, setUserVideo] = useState<File | null>(null);
  const [refMode, setRefMode] = useState<RefMode>("upload");
  const [professionalVideo, setProfessionalVideo] = useState<File | null>(null);
  const [professionalUrl, setProfessionalUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    me()
      .then(() => setCheckingAuth(false))
      .catch(() => router.replace("/login?next=/studio/upload"));
  }, [router]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!userVideo) {
      setError("Add your practice video first.");
      return;
    }
    if (refMode === "upload" && !professionalVideo) {
      setError("Add a reference video, or switch to pasting a YouTube link.");
      return;
    }
    if (refMode === "link" && !professionalUrl.trim()) {
      setError("Paste a YouTube link, or switch to uploading a file.");
      return;
    }

    setError(null);
    setPending(true);
    try {
      const { analysis_id } = await createAnalysis({
        userVideo,
        professionalVideo: refMode === "upload" ? professionalVideo ?? undefined : undefined,
        professionalVideoUrl: refMode === "link" ? professionalUrl.trim() : undefined,
      });
      router.push(`/studio/processing/${analysis_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
      setPending(false);
    }
  }

  if (checkingAuth) {
    return <div className="flex-grow flex items-center justify-center text-muted text-sm">Loading...</div>;
  }

  return (
    <>
      {rejected && (
        <div className="fixed top-4 left-4 right-4 md:left-auto md:top-6 md:right-6 z-10">
          <Toast message={rejected} onDismiss={() => setRejected(null)} />
        </div>
      )}

      <form onSubmit={handleSubmit} className="flex-grow flex flex-col">
      <div className="flex-grow flex flex-col items-center justify-center px-5 md:px-16 py-6 md:py-8 gap-[30px]">
        <div className="text-center flex flex-col gap-1.5">
          <h1 className="font-serif" style={{ fontSize: 28, fontWeight: 500 }}>
            Add your two videos
          </h1>
          <p className="text-sm text-muted">Your practice video, and a reference to compare it against.</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-7 w-full max-w-[1140px]">
          <div className="flex flex-col gap-3">
            <div className="text-sm font-semibold">Your video</div>
            <Dropzone file={userVideo} onChange={setUserVideo} height={250} />
          </div>

          <div className="flex flex-col gap-3">
            <div className="text-sm font-semibold">Reference video</div>
            <div className="flex border border-border rounded-[10px] p-1 bg-white">
              <button
                type="button"
                onClick={() => setRefMode("upload")}
                className="flex-1 rounded-lg py-2.5 text-sm font-semibold"
                style={{
                  background: refMode === "upload" ? "var(--accent)" : "transparent",
                  color: refMode === "upload" ? "#FFFFFF" : "var(--ink)",
                }}
              >
                Upload file
              </button>
              <button
                type="button"
                onClick={() => setRefMode("link")}
                className="flex-1 rounded-lg py-2.5 text-sm font-semibold"
                style={{
                  background: refMode === "link" ? "var(--accent)" : "transparent",
                  color: refMode === "link" ? "#FFFFFF" : "var(--ink)",
                }}
              >
                Paste YouTube link
              </button>
            </div>

            {refMode === "upload" ? (
              <Dropzone file={professionalVideo} onChange={setProfessionalVideo} height={194} />
            ) : (
              <div
                className="border border-border rounded-2xl flex flex-col justify-center gap-3.5 px-8 bg-white"
                style={{ height: 194 }}
              >
                <label htmlFor="yt-url" className="text-[13px] font-semibold text-muted">
                  YouTube URL
                </label>
                <input
                  id="yt-url"
                  type="url"
                  placeholder="https://youtube.com/watch?v=..."
                  value={professionalUrl}
                  onChange={(e) => setProfessionalUrl(e.target.value)}
                  className="border border-border rounded-lg px-4 py-3.5 text-[15px]"
                />
                <div className="text-[13px] text-muted">We&apos;ll fetch and validate the video before analysis.</div>
              </div>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-start justify-center gap-x-8 gap-y-4 md:gap-11">
          {[
            {
              label: "Good lighting",
              icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
                  <circle cx="12" cy="12" r="4.5" />
                  <path d="M12 3v2.5M12 18.5V21M4.2 4.2l1.8 1.8M18 18l1.8 1.8M3 12h2.5M18.5 12H21M4.2 19.8l1.8-1.8M18 6l1.8-1.8" strokeLinecap="round" />
                </svg>
              ),
            },
            {
              label: "Full body in frame",
              icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
                  <circle cx="12" cy="8" r="3.2" />
                  <path d="M5.5 20c0-4 3-6.5 6.5-6.5S18.5 16 18.5 20" strokeLinecap="round" />
                </svg>
              ),
            },
            {
              label: "Plain background",
              icon: (
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
                  <rect x="4" y="5" width="16" height="14" rx="2" />
                  <path d="M4 15l4-4 3 3 5-5 4 4" strokeLinecap="round" strokeLinejoin="round" />
                </svg>
              ),
            },
          ].map((tip) => (
            <div key={tip.label} className="flex flex-col items-center gap-2">
              <IconBadge size={52} bg="#FFFFFF" border="1px solid var(--border)">
                {tip.icon}
              </IconBadge>
              <div className="text-xs text-muted">{tip.label}</div>
            </div>
          ))}
        </div>

        {error && <div className="text-sm text-[#B0453D]">{error}</div>}
      </div>

      <footer className="flex justify-end px-5 md:px-16 py-5 border-t border-border">
        <Button type="submit" disabled={pending}>
          {pending ? "Uploading..." : "Continue"}
        </Button>
      </footer>
      </form>
    </>
  );
}

export default function UploadPage() {
  return (
    <div className="flex flex-col min-h-screen">
      <StudioHeader step={1} />
      <Suspense>
        <UploadForm />
      </Suspense>
    </div>
  );
}
