import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { expect, type Page } from "@playwright/test";

export const PASSWORD = "correct-horse-battery";

export function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

/** Registers through the real form, which signs the new user in and lands on the upload page. */
export async function registerAndOpenUpload(page: Page): Promise<void> {
  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Tester");
  await page.getByLabel("Email").fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Add your two videos")).toBeVisible();
}

/** Opens the upload page as the shared signed-in user (see auth.setup.ts). */
export async function openUpload(page: Page): Promise<void> {
  await page.goto("/studio/upload");
  await expect(page.getByText("Add your two videos")).toBeVisible();
}

/** Attaches files to the upload form's real file inputs (user video first, then reference) and submits. */
export async function attachAndSubmit(page: Page, userVideo: string, referenceVideo: string): Promise<void> {
  const inputs = page.locator('input[type="file"]');
  await inputs.nth(0).setInputFiles(userVideo);
  await inputs.nth(1).setInputFiles(referenceVideo);
  await page.getByRole("button", { name: "Continue" }).click();
}

/** The page must never scroll sideways: the classic symptom of a layout that doesn't fit. */
export async function expectNoHorizontalScroll(page: Page): Promise<void> {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
  expect(overflow, `page scrolls sideways by ${overflow}px`).toBeLessThanOrEqual(0);
}

export function hasFfmpeg(): boolean {
  try {
    execFileSync("ffmpeg", ["-version"], { stdio: "ignore" });
    return true;
  } catch {
    return false;
  }
}

function ffmpeg(args: string[]): void {
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", ...args], { stdio: "inherit" });
}

export function makeTempDir(): string {
  return fs.mkdtempSync(path.join(os.tmpdir(), "cadence-e2e-"));
}

/** A clip with nobody in it: a synthetic test pattern. */
export function makeEmptyClip(dir: string): string {
  const out = path.join(dir, "nobody-here.mp4");
  ffmpeg(["-f", "lavfi", "-i", "testsrc2=size=640x480:rate=30", "-t", "4", "-pix_fmt", "yuv420p", out]);
  return out;
}

/** Two real dancers side by side, built from two real solo clips -- the "more than one person" case. */
export function makeDuoClip(dir: string, left: string, right: string): string {
  const out = path.join(dir, "duo.mp4");
  ffmpeg([
    "-i", left,
    "-i", right,
    "-filter_complex",
    "[0:v]scale=-2:480,fps=30,setsar=1[a];[1:v]scale=-2:480,fps=30,setsar=1[b];[a][b]hstack=inputs=2:shortest=1[v]",
    "-map", "[v]", "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p",
    out,
  ]);
  return out;
}
