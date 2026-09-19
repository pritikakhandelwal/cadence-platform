export function Toast({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      className="flex gap-3.5 items-start rounded-2xl bg-white px-[22px] py-5 shadow-[0_8px_24px_rgba(43,26,92,0.14)] max-w-md"
    >
      <svg
        width="20"
        height="20"
        viewBox="0 0 24 24"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="1.8"
        className="flex-shrink-0 mt-0.5"
      >
        <circle cx="12" cy="12" r="9" />
        <path d="M12 8v5M12 16h.01" strokeLinecap="round" />
      </svg>
      <div className="flex flex-col gap-1 flex-grow">
        <div className="text-sm font-semibold text-ink">Couldn&apos;t analyze that video</div>
        <div className="text-[13px] text-muted leading-relaxed">{message}</div>
      </div>
      <button
        type="button"
        aria-label="Dismiss"
        onClick={onDismiss}
        className="text-muted-2 text-base leading-none"
      >
        &times;
      </button>
    </div>
  );
}
