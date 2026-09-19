export function IconBadge({
  children,
  size = 84,
  bg = "var(--accent-tint)",
  border,
}: {
  children: React.ReactNode;
  size?: number;
  bg?: string;
  border?: string;
}) {
  return (
    <div
      className="flex items-center justify-center rounded-full flex-shrink-0"
      style={{ width: size, height: size, background: bg, border }}
    >
      {children}
    </div>
  );
}
