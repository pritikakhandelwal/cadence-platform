import type { AnalysisResult } from "@cadence/schema";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const REQUEST_TIMEOUT_MS = 15_000;

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      ...init,
      credentials: "include",
      signal: controller.signal,
    });
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "The server is taking too long to respond. Try again in a moment.");
    }
    throw new ApiError(0, "Couldn't reach the server. Check your connection and try again.");
  } finally {
    clearTimeout(timeout);
  }

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message =
      (body && typeof body.detail === "string" && body.detail) ||
      `Request failed with status ${response.status}.`;
    throw new ApiError(response.status, message);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export interface UserOut {
  id: string;
  name: string;
  email: string;
}

export function register(input: {
  name: string;
  email: string;
  password: string;
  confirm: string;
}): Promise<{ registered: boolean }> {
  return apiFetch("/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function login(input: { email: string; password: string }): Promise<UserOut> {
  return apiFetch("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
}

export function logout(): Promise<{ loggedOut: boolean }> {
  return apiFetch("/auth/logout", { method: "POST" });
}

export function me(): Promise<UserOut> {
  return apiFetch("/auth/me");
}

export interface CreateAnalysisInput {
  userVideo: File;
  professionalVideo?: File;
  professionalVideoUrl?: string;
}

export function createAnalysis(
  input: CreateAnalysisInput
): Promise<{ analysis_id: string; status: string }> {
  const form = new FormData();
  form.set("user_video", input.userVideo);
  if (input.professionalVideo) {
    form.set("professional_video", input.professionalVideo);
  }
  if (input.professionalVideoUrl) {
    form.set("professional_video_url", input.professionalVideoUrl);
  }
  return apiFetch("/analyses", { method: "POST", body: form });
}

export function getAnalysis(analysisId: string): Promise<AnalysisResult> {
  return apiFetch(`/analyses/${analysisId}`);
}

export interface CandidateTrack {
  track_id: number;
  frame_count: number;
  mean_confidence: number;
  fragments: number;
}

export function getCandidateTracks(analysisId: string): Promise<CandidateTrack[]> {
  return apiFetch(`/analyses/${analysisId}/candidate-tracks`);
}

export function lockTrack(
  analysisId: string,
  trackId: number
): Promise<{ analysis_id: string; status: string }> {
  return apiFetch(`/analyses/${analysisId}/lock`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ track_id: trackId }),
  });
}
