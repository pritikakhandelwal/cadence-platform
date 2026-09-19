export type VideoView = "mine" | "reference";

export function VideoToggle({
  value,
  onChange,
}: {
  value: VideoView;
  onChange: (view: VideoView) => void;
}) {
  const tabStyle = (active: boolean) => ({
    background: active ? "var(--accent)" : "transparent",
    color: active ? "#FFFFFF" : "var(--muted)",
  });

  return (
    <div className="flex rounded-full p-[5px] gap-0.5" style={{ background: "#F0EAFB" }}>
      <button
        type="button"
        onClick={() => onChange("mine")}
        style={tabStyle(value === "mine")}
        className="flex items-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-semibold"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c0-4.4 3.6-8 8-8s8 3.6 8 8" strokeLinecap="round" />
        </svg>
        Your video
      </button>
      <button
        type="button"
        onClick={() => onChange("reference")}
        style={tabStyle(value === "reference")}
        className="flex items-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-semibold"
      >
        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="12" r="9" />
          <circle cx="12" cy="12" r="4" />
          <circle cx="12" cy="12" r="0.6" fill="currentColor" />
        </svg>
        Reference
      </button>
    </div>
  );
}
