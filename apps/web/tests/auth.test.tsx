import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  search: "",
  login: vi.fn(),
  register: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
  useSearchParams: () => new URLSearchParams(mocks.search),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  login: mocks.login,
  register: mocks.register,
}));

import LoginPage from "@/app/login/page";
import RegisterPage from "@/app/register/page";

beforeEach(() => {
  mocks.router.push.mockReset();
  mocks.search = "";
  mocks.login.mockReset();
  mocks.register.mockReset();
});

describe("LoginPage", () => {
  async function submit(email = "ada@example.com", password = "secret-pass") {
    await userEvent.type(screen.getByLabelText("Email"), email);
    await userEvent.type(screen.getByLabelText("Password"), password);
    await userEvent.click(screen.getByRole("button", { name: /log in/i }));
  }

  it("logs in and goes to the studio by default", async () => {
    mocks.login.mockResolvedValue({ id: "1", name: "Ada", email: "ada@example.com" });
    render(<LoginPage />);

    await submit();

    expect(mocks.login).toHaveBeenCalledWith({ email: "ada@example.com", password: "secret-pass" });
    expect(mocks.router.push).toHaveBeenCalledWith("/studio/upload");
  });

  it("returns to the page that sent them to log in", async () => {
    mocks.search = "next=/studio/results/abc";
    mocks.login.mockResolvedValue({ id: "1", name: "Ada", email: "ada@example.com" });
    render(<LoginPage />);

    await submit();

    expect(mocks.router.push).toHaveBeenCalledWith("/studio/results/abc");
  });

  it("shows the server's reason and doesn't navigate when login fails", async () => {
    mocks.login.mockRejectedValue(new ApiError(401, "Incorrect email or password."));
    render(<LoginPage />);

    await submit();

    expect(await screen.findByText("Incorrect email or password.")).toBeInTheDocument();
    expect(mocks.router.push).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: /log in/i })).toBeEnabled();
  });

  it("falls back to a generic message for a non-API failure", async () => {
    mocks.login.mockRejectedValue(new Error("boom"));
    render(<LoginPage />);

    await submit();

    expect(await screen.findByText("Something went wrong. Try again.")).toBeInTheDocument();
  });

  it("links to registration", () => {
    render(<LoginPage />);
    expect(screen.getByRole("link", { name: /create an account/i })).toHaveAttribute("href", "/register");
  });
});

describe("RegisterPage", () => {
  async function fill(password = "correct-horse", confirm = "correct-horse") {
    await userEvent.type(screen.getByLabelText("Name"), "Ada Lovelace");
    await userEvent.type(screen.getByLabelText("Email"), "ada@example.com");
    await userEvent.type(screen.getByLabelText("Password"), password);
    await userEvent.type(screen.getByLabelText("Confirm password"), confirm);
    await userEvent.click(screen.getByRole("button", { name: /create account/i }));
  }

  it("creates the account, logs in straight away, and lands in the studio", async () => {
    mocks.register.mockResolvedValue({ registered: true });
    mocks.login.mockResolvedValue({ id: "1", name: "Ada Lovelace", email: "ada@example.com" });
    render(<RegisterPage />);

    await fill();

    expect(mocks.register).toHaveBeenCalledWith({
      name: "Ada Lovelace",
      email: "ada@example.com",
      password: "correct-horse",
      confirm: "correct-horse",
    });
    // registration doesn't set a session cookie, so it has to log in as well
    expect(mocks.login).toHaveBeenCalledWith({ email: "ada@example.com", password: "correct-horse" });
    expect(mocks.router.push).toHaveBeenCalledWith("/studio/upload");
  });

  it("shows the server's reason and doesn't try to log in when registration fails", async () => {
    mocks.register.mockRejectedValue(new ApiError(400, "That email is already registered."));
    render(<RegisterPage />);

    await fill();

    expect(await screen.findByText("That email is already registered.")).toBeInTheDocument();
    expect(mocks.login).not.toHaveBeenCalled();
    expect(mocks.router.push).not.toHaveBeenCalled();
  });

  it("links back to login", () => {
    render(<RegisterPage />);
    expect(screen.getByRole("link", { name: /^log in$/i })).toHaveAttribute("href", "/login");
  });
});
