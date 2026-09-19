import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";
import { makeAnalysis } from "./helpers";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getAnalysis: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => mocks.router }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAnalysis: mocks.getAnalysis,
}));

import { ProcessingClient } from "@/app/studio/processing/[id]/ProcessingClient";

beforeEach(() => {
  vi.useFakeTimers();
  mocks.router.push.mockReset();
  mocks.router.replace.mockReset();
  mocks.getAnalysis.mockReset();
});

afterEach(() => {
  vi.useRealTimers();
});

// act() so React state updates triggered by resolved/rejected promises land
// in the DOM; the fake clock is why findBy* (which polls on real timers) can't be used here.
async function flush(ms = 0) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe("ProcessingClient", () => {
  it("keeps polling while the analysis is queued or running, and goes to results when it completes", async () => {
    mocks.getAnalysis
      .mockResolvedValueOnce(makeAnalysis("queued"))
      .mockResolvedValueOnce(makeAnalysis("running"))
      .mockResolvedValueOnce(makeAnalysis("complete"));

    render(<ProcessingClient id="abc" />);
    await flush();
    expect(mocks.getAnalysis).toHaveBeenCalledTimes(1);
    expect(mocks.router.replace).not.toHaveBeenCalled();

    await flush(2500);
    expect(mocks.getAnalysis).toHaveBeenCalledTimes(2);
    expect(mocks.router.replace).not.toHaveBeenCalled();

    await flush(2500);
    expect(mocks.router.replace).toHaveBeenCalledWith("/studio/results/abc");
  });

  it("sends the person to pick a dancer when the lock is ambiguous", async () => {
    mocks.getAnalysis.mockResolvedValue(makeAnalysis("needs_dancer_pick"));

    render(<ProcessingClient id="abc" />);
    await flush();

    expect(mocks.router.replace).toHaveBeenCalledWith("/studio/pick/abc");
  });

  it("returns to upload with the reason when the analysis is rejected", async () => {
    mocks.getAnalysis.mockResolvedValue(
      makeAnalysis("rejected", { quality_gate: { passed: false, reasons: ["Only 40% of frames were usable."] } })
    );

    render(<ProcessingClient id="abc" />);
    await flush();

    expect(mocks.router.replace).toHaveBeenCalledWith(
      `/studio/upload?rejected=${encodeURIComponent("Only 40% of frames were usable.")}`
    );
  });

  it("falls back to a generic reason when a rejection carries none", async () => {
    mocks.getAnalysis.mockResolvedValue(makeAnalysis("rejected"));

    render(<ProcessingClient id="abc" />);
    await flush();

    expect(mocks.router.replace).toHaveBeenCalledWith(
      `/studio/upload?rejected=${encodeURIComponent("This video couldn't be analyzed.")}`
    );
  });

  it("sends a logged-out visitor to log in, and back here afterwards", async () => {
    mocks.getAnalysis.mockRejectedValue(new ApiError(401, "Not authenticated."));

    render(<ProcessingClient id="abc" />);
    await flush();

    expect(mocks.router.replace).toHaveBeenCalledWith("/login?next=/studio/processing/abc");
  });

  it("redirects only once, even if more polls land before the navigation finishes", async () => {
    mocks.getAnalysis.mockResolvedValue(makeAnalysis("complete"));

    render(<ProcessingClient id="abc" />);
    await flush();
    await flush(10_000);

    expect(mocks.router.replace).toHaveBeenCalledTimes(1);
  });

  it("stops polling when the page unmounts", async () => {
    mocks.getAnalysis.mockResolvedValue(makeAnalysis("running"));

    const { unmount } = render(<ProcessingClient id="abc" />);
    await flush();
    unmount();
    const callsAtUnmount = mocks.getAnalysis.mock.calls.length;

    await flush(10_000);
    expect(mocks.getAnalysis).toHaveBeenCalledTimes(callsAtUnmount);
  });

  it("shows a connection problem without giving up, so a blip doesn't strand the person", async () => {
    mocks.getAnalysis
      .mockRejectedValueOnce(new ApiError(0, "Couldn't reach the server. Check your connection and try again."))
      .mockResolvedValueOnce(makeAnalysis("complete"));

    render(<ProcessingClient id="abc" />);
    await flush();
    expect(screen.getByText(/couldn't reach the server/i)).toBeInTheDocument();

    await flush(2500);
    expect(mocks.router.replace).toHaveBeenCalledWith("/studio/results/abc");
  });

  it("stops promising it'll be quick once it has been waiting a few minutes", async () => {
    mocks.getAnalysis.mockResolvedValue(makeAnalysis("running"));

    render(<ProcessingClient id="abc" />);
    await flush();
    expect(screen.getByText("This usually takes under a minute.")).toBeInTheDocument();

    await flush(3 * 60_000);
    expect(screen.getByText(/taking longer than usual/i)).toBeInTheDocument();
    expect(screen.queryByText("This usually takes under a minute.")).not.toBeInTheDocument();
    // still polling -- it's a hint, not a give-up
    expect(mocks.router.replace).not.toHaveBeenCalled();
  });
});
