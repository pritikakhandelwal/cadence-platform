import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError, createAnalysis, lockTrack, me } from "@/lib/api";

const fetchMock = vi.fn();

function jsonResponse(body: unknown, init: { ok?: boolean; status?: number } = {}) {
  return { ok: init.ok ?? true, status: init.status ?? 200, json: async () => body };
}

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe("apiFetch (via me)", () => {
  it("always sends the session cookie and parses the JSON body", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ id: "1", name: "Ada", email: "a@b.c" }));

    await expect(me()).resolves.toEqual({ id: "1", name: "Ada", email: "a@b.c" });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/auth/me");
    expect(init.credentials).toBe("include");
  });

  it("surfaces the server's detail message on an error response", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ detail: "Not authenticated." }, { ok: false, status: 401 }));

    await expect(me()).rejects.toMatchObject({ name: "Error", status: 401, message: "Not authenticated." });
    await expect(me()).rejects.toBeInstanceOf(ApiError);
  });

  it("falls back to a status message when the error body isn't JSON", async () => {
    fetchMock.mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => {
        throw new SyntaxError("not json");
      },
    });

    await expect(me()).rejects.toMatchObject({ status: 500, message: "Request failed with status 500." });
  });

  it("reports an unreachable server as status 0", async () => {
    fetchMock.mockRejectedValue(new TypeError("Failed to fetch"));

    await expect(me()).rejects.toMatchObject({ status: 0, message: expect.stringMatching(/reach the server/i) });
  });

  it("gives up on a hung request after 15s instead of spinning forever", async () => {
    vi.useFakeTimers();
    fetchMock.mockImplementation(
      (_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener("abort", () => reject(new DOMException("Aborted", "AbortError")));
        })
    );

    const outcome = expect(me()).rejects.toMatchObject({
      status: 0,
      message: expect.stringMatching(/too long/i),
    });
    await vi.advanceTimersByTimeAsync(15_000);
    await outcome;
  });
});

describe("createAnalysis", () => {
  const video = (name: string) => new File(["x"], name, { type: "video/mp4" });

  it("sends the reference as a file when one is given", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ analysis_id: "a1", status: "queued" }));

    await createAnalysis({ userVideo: video("me.mp4"), professionalVideo: video("pro.mp4") });

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/analyses");
    expect(init.method).toBe("POST");
    const form = init.body as FormData;
    expect((form.get("user_video") as File).name).toBe("me.mp4");
    expect((form.get("professional_video") as File).name).toBe("pro.mp4");
    expect(form.has("professional_video_url")).toBe(false);
  });

  it("sends the reference as a URL when that's what was given", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ analysis_id: "a1", status: "queued" }));

    await createAnalysis({
      userVideo: video("me.mp4"),
      professionalVideoUrl: "https://youtube.com/watch?v=abc",
    });

    const form = fetchMock.mock.calls[0][1].body as FormData;
    expect(form.get("professional_video_url")).toBe("https://youtube.com/watch?v=abc");
    expect(form.has("professional_video")).toBe(false);
  });

  it("doesn't set a Content-Type, so the browser can add the multipart boundary", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ analysis_id: "a1", status: "queued" }));

    await createAnalysis({ userVideo: video("me.mp4"), professionalVideoUrl: "https://youtu.be/x" });

    expect(fetchMock.mock.calls[0][1].headers).toBeUndefined();
  });
});

describe("lockTrack", () => {
  it("posts the chosen track id as JSON", async () => {
    fetchMock.mockResolvedValue(jsonResponse({ analysis_id: "a1", status: "running" }));

    await lockTrack("a1", 3);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("http://localhost:8000/analyses/a1/lock");
    expect(JSON.parse(init.body)).toEqual({ track_id: 3 });
    expect(init.headers).toEqual({ "Content-Type": "application/json" });
  });
});
