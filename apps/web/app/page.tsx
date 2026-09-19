import Link from "next/link";
import { Logo } from "@/components/Logo";
import { LinkButton } from "@/components/Button";
import { IconBadge } from "@/components/IconBadge";

const STEPS = [
  {
    label: "Upload",
    caption: "Two videos, side by side",
    icon: (
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
        <path
          d="M12 15V3m0 0l-4 4m4-4l4 4M4 17v2a2 2 0 002 2h12a2 2 0 002-2v-2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    ),
  },
  {
    label: "Compare",
    caption: "Joint by joint",
    icon: (
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
        <circle cx="9" cy="12" r="6" />
        <circle cx="16" cy="12" r="6" />
      </svg>
    ),
  },
  {
    label: "Improve",
    caption: "Track your growth",
    icon: (
      <svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="var(--accent)" strokeWidth="1.7">
        <path d="M3 17l6-6 4 4 8-8" strokeLinecap="round" strokeLinejoin="round" />
        <path d="M15 7h6v6" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    ),
  },
];

export default function Home() {
  return (
    <div className="flex flex-col min-h-screen">
      <header className="flex items-center justify-between px-16 py-7">
        <Logo />
        <nav className="flex items-center gap-9">
          <Link href="#how-it-works" className="text-[15px] no-underline text-ink">
            How it works
          </Link>
          <Link href="/login" className="text-[15px] no-underline text-ink">
            Log in
          </Link>
          <LinkButton href="/studio/upload" className="!px-6 !py-3">
            Get started
          </LinkButton>
        </nav>
      </header>

      <div className="relative mx-16 rounded-[20px] overflow-hidden flex-shrink-0" style={{ height: 620 }}>
        <video autoPlay muted loop playsInline className="absolute inset-0 w-full h-full object-cover" style={{ background: "#171522" }} />
        <div className="absolute inset-0" style={{ background: "rgba(30, 20, 60, 0.42)" }} />
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center gap-6 px-20">
          <div
            className="font-serif italic text-white"
            style={{ fontSize: 88, lineHeight: 1, fontWeight: 500, letterSpacing: "-0.02em" }}
          >
            Cadence
          </div>
          <h1 className="font-serif text-white max-w-[620px]" style={{ fontSize: 32, fontWeight: 500, lineHeight: 1.3 }}>
            Train like a professional, one move at a time.
          </h1>
          <p className="text-white/80 max-w-[500px]" style={{ fontSize: 16, lineHeight: 1.55 }}>
            See exactly where your technique differs, move by move.
          </p>
          <div className="flex gap-4 mt-1.5">
            <LinkButton href="/studio/upload" variant="primary">
              Start your analysis
            </LinkButton>
            <LinkButton href="#how-it-works" variant="outline-light">
              See how it works
            </LinkButton>
          </div>
        </div>
      </div>

      <div id="how-it-works" className="flex-grow flex flex-col items-center justify-center gap-10 px-16 py-10">
        <div className="text-center flex flex-col gap-2">
          <div
            className="text-[13px] font-semibold uppercase text-accent"
            style={{ letterSpacing: "0.08em" }}
          >
            How it works
          </div>
          <h2 className="font-serif" style={{ fontSize: 26, fontWeight: 500 }}>
            Three simple steps.
          </h2>
        </div>

        <div className="flex items-start justify-center w-full max-w-[880px]">
          {STEPS.map((step, i) => (
            <div key={step.label} className="contents">
              <div className="flex flex-col items-center gap-2.5 w-40">
                <IconBadge>{step.icon}</IconBadge>
                <div className="text-[16px] font-semibold">{step.label}</div>
                <div className="text-[13px] text-muted text-center">{step.caption}</div>
              </div>
              {i < STEPS.length - 1 && (
                <div
                  className="flex-1 max-w-[90px]"
                  style={{ height: 0, borderTop: "2px dashed #D8CFF2", marginTop: 42 }}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      <footer className="flex items-center justify-between px-16 py-[22px] border-t border-border">
        <div className="text-[13px] text-muted">© 2026 Cadence</div>
        <div className="flex gap-6">
          <Link href="#" className="text-[13px] no-underline text-muted">
            Privacy
          </Link>
          <Link href="#" className="text-[13px] no-underline text-muted">
            Terms
          </Link>
        </div>
      </footer>
    </div>
  );
}
