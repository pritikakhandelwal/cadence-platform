import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";
import { makeAnalysis, makeCompleteAnalysis } from "./helpers";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getAnalysis: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => mocks.router }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getAnalysis: mocks.getAnalysis,
}));

import { ResultsClient } from "@/app/studio/results/[id]/ResultsClient";

beforeEach(() => {
  mocks.router.replace.mockReset();
  mocks.getAnalysis.mockReset();
});

const seg = (t0: number, t1: number, issues: { type: string; joint: string; message: string }[]) => ({
  t0,
  t1,
  score: 50,
  confidence: 1,
  issues: issues.map((i) => ({ ...i, type: i.type as never, magnitude: 1 })),
});

describe("ResultsClient", () => {
  it("shows the real score, method and tracking stats from the analysis", async () => {
    mocks.getAnalysis.mockResolvedValue(makeCompleteAnalysis([]));
    render(<ResultsClient id="abc" />);

    expect(await screen.findByText("38.6")).toBeInTheDocument();
    expect(screen.getByText("angle-dtw-v2 · v2")).toBeInTheDocument();
    expect(screen.getByText("90%")).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText("2")).toBeInTheDocument();
  });

  it("lists every issue chronologically with its type label and message", async () => {
    mocks.getAnalysis.mockResolvedValue(
      makeCompleteAnalysis([
        seg(0, 2, [{ type: "angle", joint: "left_elbow", message: "Left Elbow off by about 27 degrees." }]),
        seg(2, 4, [
          { type: "occlusion", joint: "right_knee", message: "Right Knee wasn't visible enough." },
          { type: "timing", joint: "overall", message: "Running 0.3s ahead of the reference." },
        ]),
      ])
    );
    render(<ResultsClient id="abc" />);

    const timeline = (await screen.findByRole("heading", { name: "Timeline" })).parentElement!;
    const text = timeline.textContent!;
    expect(text.indexOf("Left Elbow off by about 27 degrees.")).toBeLessThan(
      text.indexOf("Right Knee wasn't visible enough.")
    );
    expect(text.indexOf("Right Knee wasn't visible enough.")).toBeLessThan(
      text.indexOf("Running 0.3s ahead of the reference.")
    );
    expect(within(timeline).getAllByText("Occlusion").length).toBeGreaterThan(0);
    expect(within(timeline).getAllByText("Timing").length).toBeGreaterThan(0);
  });

  it("formats issue times as m:ss from the segment start", async () => {
    mocks.getAnalysis.mockResolvedValue(
      makeCompleteAnalysis([seg(65, 67, [{ type: "angle", joint: "left_hip", message: "Left Hip off." }])])
    );
    render(<ResultsClient id="abc" />);

    expect(await screen.findByText("1:05")).toBeInTheDocument();
  });

  it("shows the reference explainer, not an empty timeline, when nothing was flagged", async () => {
    mocks.getAnalysis.mockResolvedValue(makeCompleteAnalysis([seg(0, 2, [])]));
    render(<ResultsClient id="abc" />);

    expect(await screen.findByText("What Cadence looks for")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Timeline" })).not.toBeInTheDocument();
  });

  it("shows dashes rather than invented numbers when there's no score yet", async () => {
    mocks.getAnalysis.mockResolvedValue(makeAnalysis("complete", { overall: null }));
    render(<ResultsClient id="abc" />);

    expect(await screen.findByText("Your result appears here")).toBeInTheDocument();
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(4);
  });

  it("sends people back to processing if the analysis isn't finished", async () => {
    mocks.getAnalysis.mockResolvedValue(
      makeAnalysis("running", { quality_gate: { passed: false, reasons: ["Analysis has not been processed yet."] } })
    );
    render(<ResultsClient id="abc" />);

    expect(await screen.findByText(/isn't finished yet \(running\)/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to processing/i })).toHaveAttribute(
      "href",
      "/studio/processing/abc"
    );
  });

  it("switches the video label when toggling between your video and the reference", async () => {
    mocks.getAnalysis.mockResolvedValue(makeCompleteAnalysis([]));
    render(<ResultsClient id="abc" />);
    await screen.findByText("38.6");

    expect(screen.getAllByText("Your video").length).toBeGreaterThan(0);
    await userEvent.click(screen.getByRole("button", { name: /reference/i }));
    expect(screen.getByText("Reference video")).toBeInTheDocument();
  });

  it("shows the server's message with a way forward when the analysis can't be loaded", async () => {
    mocks.getAnalysis.mockRejectedValue(new ApiError(404, "Analysis not found."));
    render(<ResultsClient id="abc" />);

    expect(await screen.findByText("Analysis not found.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /start a new analysis/i })).toBeInTheDocument();
  });

  it("sends a logged-out visitor to log in, and back here afterwards", async () => {
    mocks.getAnalysis.mockRejectedValue(new ApiError(401, "Not authenticated."));
    render(<ResultsClient id="abc" />);

    await vi.waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/login?next=/studio/results/abc"));
  });
});
