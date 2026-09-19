import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const mocks = vi.hoisted(() => ({
  router: { push: vi.fn(), replace: vi.fn() },
  search: "",
  me: vi.fn(),
  createAnalysis: vi.fn(),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => mocks.router,
  useSearchParams: () => new URLSearchParams(mocks.search),
}));
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  me: mocks.me,
  createAnalysis: mocks.createAnalysis,
}));

import UploadPage from "@/app/studio/upload/page";

const video = (name: string) => new File(["x"], name, { type: "video/mp4" });
const fileInputs = (container: HTMLElement) =>
  Array.from(container.querySelectorAll<HTMLInputElement>('input[type="file"]'));

beforeEach(() => {
  mocks.router.push.mockReset();
  mocks.router.replace.mockReset();
  mocks.search = "";
  mocks.me.mockReset().mockResolvedValue({ id: "1", name: "Ada", email: "a@b.c" });
  mocks.createAnalysis.mockReset();
});

async function renderReady() {
  const utils = render(<UploadPage />);
  await screen.findByText("Add your two videos");
  return utils;
}

describe("UploadPage", () => {
  it("sends a logged-out visitor to log in, and back here afterwards", async () => {
    mocks.me.mockRejectedValue(new ApiError(401, "Not authenticated."));
    render(<UploadPage />);

    await vi.waitFor(() => expect(mocks.router.replace).toHaveBeenCalledWith("/login?next=/studio/upload"));
    expect(screen.queryByText("Add your two videos")).not.toBeInTheDocument();
  });

  it("asks for the practice video first", async () => {
    await renderReady();

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText("Add your practice video first.")).toBeInTheDocument();
    expect(mocks.createAnalysis).not.toHaveBeenCalled();
  });

  it("asks for a reference in file mode", async () => {
    const { container } = await renderReady();
    await userEvent.upload(fileInputs(container)[0], video("me.mp4"));

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(/add a reference video/i)).toBeInTheDocument();
    expect(mocks.createAnalysis).not.toHaveBeenCalled();
  });

  it("asks for a link in YouTube mode, and ignores a blank one", async () => {
    const { container } = await renderReady();
    await userEvent.upload(fileInputs(container)[0], video("me.mp4"));
    await userEvent.click(screen.getByRole("button", { name: /paste youtube link/i }));
    await userEvent.type(screen.getByLabelText("YouTube URL"), "   ");

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(screen.getByText(/paste a youtube link/i)).toBeInTheDocument();
    expect(mocks.createAnalysis).not.toHaveBeenCalled();
  });

  it("submits both files and goes to processing", async () => {
    mocks.createAnalysis.mockResolvedValue({ analysis_id: "new1", status: "queued" });
    const { container } = await renderReady();
    const mine = video("me.mp4");
    const pro = video("pro.mp4");
    const [mineInput, proInput] = fileInputs(container);
    await userEvent.upload(mineInput, mine);
    await userEvent.upload(proInput, pro);

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(mocks.createAnalysis).toHaveBeenCalledWith({
      userVideo: mine,
      professionalVideo: pro,
      professionalVideoUrl: undefined,
    });
    expect(mocks.router.push).toHaveBeenCalledWith("/studio/processing/new1");
  });

  it("submits a trimmed YouTube link instead of a reference file", async () => {
    mocks.createAnalysis.mockResolvedValue({ analysis_id: "new2", status: "queued" });
    const { container } = await renderReady();
    const mine = video("me.mp4");
    await userEvent.upload(fileInputs(container)[0], mine);
    await userEvent.click(screen.getByRole("button", { name: /paste youtube link/i }));
    await userEvent.type(screen.getByLabelText("YouTube URL"), "  https://youtu.be/abc  ");

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(mocks.createAnalysis).toHaveBeenCalledWith({
      userVideo: mine,
      professionalVideo: undefined,
      professionalVideoUrl: "https://youtu.be/abc",
    });
    expect(mocks.router.push).toHaveBeenCalledWith("/studio/processing/new2");
  });

  it("doesn't send a previously-chosen reference file after switching to a link", async () => {
    mocks.createAnalysis.mockResolvedValue({ analysis_id: "new3", status: "queued" });
    const { container } = await renderReady();
    const [mineInput, proInput] = fileInputs(container);
    await userEvent.upload(mineInput, video("me.mp4"));
    await userEvent.upload(proInput, video("stale.mp4"));
    await userEvent.click(screen.getByRole("button", { name: /paste youtube link/i }));
    await userEvent.type(screen.getByLabelText("YouTube URL"), "https://youtu.be/abc");

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(mocks.createAnalysis.mock.calls[0][0].professionalVideo).toBeUndefined();
  });

  it("shows the server's rejection and stays put, so they can fix it and retry", async () => {
    mocks.createAnalysis.mockRejectedValue(new ApiError(400, "Video is longer than 5 minutes."));
    const { container } = await renderReady();
    const [mineInput, proInput] = fileInputs(container);
    await userEvent.upload(mineInput, video("me.mp4"));
    await userEvent.upload(proInput, video("pro.mp4"));

    await userEvent.click(screen.getByRole("button", { name: "Continue" }));

    expect(await screen.findByText("Video is longer than 5 minutes.")).toBeInTheDocument();
    expect(mocks.router.push).not.toHaveBeenCalled();
    expect(screen.getByRole("button", { name: "Continue" })).toBeEnabled();
  });

  it("explains a rejected analysis with a dismissible notice", async () => {
    mocks.search = "rejected=" + encodeURIComponent("Only 40% of frames were usable.");
    await renderReady();

    expect(screen.getByText("Only 40% of frames were usable.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));
    expect(screen.queryByText("Only 40% of frames were usable.")).not.toBeInTheDocument();
  });
});
