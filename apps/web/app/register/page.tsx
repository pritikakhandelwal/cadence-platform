"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { Logo } from "@/components/Logo";
import { Button } from "@/components/Button";
import { register, login, ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setPending(true);
    try {
      await register({ name, email, password, confirm });
      // Registration doesn't set a session cookie itself -- log in right
      // after so the person lands in the studio flow already signed in.
      await login({ email, password });
      router.push("/studio/upload");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Try again.");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="flex flex-col min-h-screen items-center justify-center px-6">
      <div className="w-full max-w-sm flex flex-col gap-8">
        <div className="text-center flex flex-col gap-1">
          <Logo size={26} />
          <p className="text-sm text-muted mt-2">Create an account to get started.</p>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="flex flex-col gap-1.5">
            <label htmlFor="name" className="text-[13px] font-semibold text-muted">
              Name
            </label>
            <input
              id="name"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="border border-border rounded-lg px-4 py-3 text-[15px] bg-white"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="email" className="text-[13px] font-semibold text-muted">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="border border-border rounded-lg px-4 py-3 text-[15px] bg-white"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="password" className="text-[13px] font-semibold text-muted">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="border border-border rounded-lg px-4 py-3 text-[15px] bg-white"
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor="confirm" className="text-[13px] font-semibold text-muted">
              Confirm password
            </label>
            <input
              id="confirm"
              type="password"
              required
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              className="border border-border rounded-lg px-4 py-3 text-[15px] bg-white"
            />
          </div>

          {error && <div className="text-sm text-[#B0453D]">{error}</div>}

          <Button type="submit" disabled={pending} className="mt-1">
            {pending ? "Creating account..." : "Create account"}
          </Button>
        </form>

        <p className="text-center text-sm text-muted">
          Already have an account?{" "}
          <Link href="/login" className="text-accent font-semibold no-underline">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
