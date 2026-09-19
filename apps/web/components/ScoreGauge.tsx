export function ScoreGauge({ score, size = 140 }: { score: number | null; size?: number }) {
  const r = size / 2 - 10;
  const c = 2 * Math.PI * r;
  const fraction = score === null ? 0.5 : Math.max(0, Math.min(1, score / 100));
  const offset = c * (1 - fraction);
  const center = size / 2;

  return (
    <div className="relative flex-shrink-0" style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={center} cy={center} r={r} fill="none" stroke="#EFE9FB" strokeWidth="10" />
        <circle
          cx={center}
          cy={center}
          r={r}
          fill="none"
          stroke={score === null ? "#D8CFF2" : "#7B64D9"}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${center} ${center})`}
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div
          className="font-serif"
          style={{ fontSize: size * 0.24, fontWeight: 500, color: score === null ? "#A99FC9" : "var(--ink)" }}
        >
          {score === null ? "—" : score.toFixed(1)}
        </div>
        <div className="text-xs" style={{ color: score === null ? "#A99FC9" : "var(--muted)" }}>
          / 100
        </div>
      </div>
    </div>
  );
}
