import Link from "next/link";
import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "outline" | "outline-light" | "ghost";

const base =
  "inline-flex items-center justify-center gap-2 rounded-lg text-[15px] font-semibold px-7 py-3.5 transition-colors disabled:opacity-50 disabled:cursor-not-allowed";

const variants: Record<Variant, string> = {
  primary: "bg-accent text-white hover:bg-[#6a54c9]",
  outline: "border border-border bg-white text-ink hover:bg-accent-tint",
  "outline-light": "border border-white/50 text-white hover:bg-white/10",
  ghost: "text-muted hover:text-ink",
};

interface CommonProps {
  variant?: Variant;
  className?: string;
  children: React.ReactNode;
}

export function Button({
  variant = "primary",
  className = "",
  children,
  ...rest
}: CommonProps & ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button className={`${base} ${variants[variant]} ${className}`} {...rest}>
      {children}
    </button>
  );
}

export function LinkButton({
  href,
  variant = "primary",
  className = "",
  children,
}: CommonProps & { href: string }) {
  return (
    <Link href={href} className={`${base} ${variants[variant]} ${className}`}>
      {children}
    </Link>
  );
}
