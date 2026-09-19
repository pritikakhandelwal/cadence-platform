import Link from "next/link";

export function Logo({ size = 22 }: { size?: number }) {
  return (
    <Link
      href="/"
      className="font-serif italic tracking-tight text-ink no-underline"
      style={{ fontSize: size, fontWeight: 500, letterSpacing: "-0.01em" }}
    >
      Cadence
    </Link>
  );
}
