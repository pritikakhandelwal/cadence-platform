import { Logo } from "./Logo";

export function StudioHeader({ step }: { step: 1 | 2 | 3 }) {
  return (
    <header className="flex items-center justify-between px-16 py-6 border-b border-border">
      <Logo />
      <div className="flex items-center gap-2.5 text-[13px] text-muted">
        <span>Step {step} of 3</span>
        <div className="flex gap-1.5">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className="h-1 w-[22px] rounded-full"
              style={{ background: n <= step ? "var(--accent)" : "var(--border)" }}
            />
          ))}
        </div>
      </div>
    </header>
  );
}
