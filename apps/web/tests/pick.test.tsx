import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  getCandidateTracks: vi.fn(),
  lockTrack: vi.fn(),
}));

vi.mock("next/navigation", () => ({ useRouter: () => mocks.router }));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  getCandidateTracks: mocks.getCandidateTracks,
  lockTrack: mocks.lockTrack,
}));

import { PickClient } from "@/app/studio/pick/[id]/PickClient";

const TRACKS = [
  { track_id: 1, frame_count: 400, mean_confidence: 0.91, fragments: 1 },
  { track_id: 4, frame_count: 210, mean_confidence: 0.68, fragments: 3 },
];

beforeEach(() => {
  mocks.router.push.mockReset();
  mocks.router.replace.mockReset();
  mocks.getCandidateTracks.mockReset().mockResolvedValue(TRACKS);
  mocks.lockTrack.mockReset();
});

const continueButton = () => screen.getByRole("button", { name: /continue|locking/i });

describe("PickClient", () => {
  it("lists each candidate the backend found, labelled by its real track id", async () => {
    render(<PickClient id="abc" />);

    expect(await screen.findByText("Person 1")).toBeInTheDocument();
    expect(screen.getByText("Person 4")).toBeInTheDocument();
    expect(mocks.getCandidateTracks).toHaveBeenCalledWith("abc");
  });

  it("won't continue until someone is picked", async () => {
    render(<PickClient id="abc" />);
    await screen.findByText("Person 1");

    expect(continueButton()).toBeDisabled();
    await userEvent.click(screen.getByText("Person 4"));
    expect(continueButton()).toBeEnabled();
  });

  it("locks onto the picked track and goes back to processing", async () => {
    mocks.lockTrack.mockResolvedValue({ analysis_id: "abc", status: "running" });
    render(<PickClient id="abc" />);
    await screen.findByText("Person 1");

    await userEvent.click(screen.getByText("Person 4"));
    await userEvent.click(continueButton());

    expect(mocks.lockTrack).toHaveBeenCalledWith("abc", 4);
    expect(mocks.router.push).toHaveBeenCalledWith("/studio/processing/abc");
  });

  it("shows the server's reason and lets them retry if locking fails", async () => {
    mocks.lockTrack.mockRejectedValue(new ApiError(400, "Unknown track_id for this analysis."));
    render(<PickClient id="abc" />);
    await screen.findByText("Person 1");

    await userEvent.click(screen.getByText("Person 1"));
    await userEvent.click(continueButton());

    expect(await screen.findByText("Unknown track_id for this analysis.")).toBeInTheDocument();
    expect(mocks.router.push).not.toHaveBeenCalled();
    expect(continueButton()).toBeEnabled();
  });

  it("sends a logged-out visitor to log in, and back here afterwards", async () => {
    mocks.getCandidateTracks.mockRejectedValue(new ApiError(401, "Not authenticated."));
    render(<PickClient id="abc" />);

    await vi.waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/login?next=/studio/pick/abc"));
  });

  it("explains itself if the analysis isn't waiting for a pick", async () => {
    mocks.getCandidateTracks.mockRejectedValue(new ApiError(400, "This analysis isn't waiting for a dancer pick."));
    render(<PickClient id="abc" />);

    expect(await screen.findByText("This analysis isn't waiting for a dancer pick.")).toBeInTheDocument();
  });
});
