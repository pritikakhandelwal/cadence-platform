import path from "node:path";
import { expect, test } from "@playwright/test";
import {
  attachAndSubmit,
  expectNoHorizontalScroll,
  hasFfmpeg,
  makeDuoClip,
  makeEmptyClip,
  makeTempDir,
  openUpload,
} from "./helpers";

// The unhappy and branching paths, through the real UI, API, queue and worker.
// Needs ffmpeg (to build the test clips) and two real solo dance clips.
const USER_VIDEO = process.env.CADENCE_E2E_USER_VIDEO;
const REFERENCE_VIDEO = process.env.CADENCE_E2E_REFERENCE_VIDEO;

test.skip(!hasFfmpeg(), "ffmpeg isn't on PATH (needed to build the test clips)");

const needsClips = !USER_VIDEO || !REFERENCE_VIDEO;
const clipsReason = "set CADENCE_E2E_USER_VIDEO and CADENCE_E2E_REFERENCE_VIDEO (see e2e/README.md)";

let dir: string;
test.beforeAll(() => {
  dir = makeTempDir();
});

test("a pasted link that isn't YouTube is refused with a reason, before anything is downloaded", async ({ page }) => {
  await openUpload(page);
  const clip = makeEmptyClip(dir);

  await page.locator('input[type="file"]').nth(0).setInputFiles(clip);
  await page.getByRole("button", { name: /paste youtube link/i }).click();
  await page.getByLabel("YouTube URL").fill("https://example.com/not-youtube.mp4");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByText(/youtube/i).filter({ hasNotText: /paste|url|link\b/i }).first()).toBeVisible();
  await expect(page).toHaveURL(/\/studio\/upload/);
  await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();
});

test("a video with nobody in it is refused with a reason, and they can try again", async ({ page }) => {
  test.skip(needsClips, clipsReason);
  await openUpload(page);

  await attachAndSubmit(page, makeEmptyClip(dir), REFERENCE_VIDEO!);
  await page.waitForURL(/\/studio\/processing\//);

  await page.waitForURL(/\/studio\/upload\?rejected=/, { timeout: 4 * 60_000 });
  await expect(page.getByText("Couldn't analyze that video")).toBeVisible();
  await expect(page.getByText(/no person detected/i)).toBeVisible();

  await page.getByRole("button", { name: /dismiss/i }).click();
  await expect(page.getByText("Couldn't analyze that video")).not.toBeVisible();
  await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();
});

test("two people in the video: pick which one is you, then get a real result", async ({ page }) => {
  test.skip(needsClips, clipsReason);
  await openUpload(page);

  await attachAndSubmit(page, makeDuoClip(dir, REFERENCE_VIDEO!, USER_VIDEO!), REFERENCE_VIDEO!);
  await page.waitForURL(/\/studio\/pick\//, { timeout: 5 * 60_000 });

  // the page navigates before the candidate tracks have loaded -- wait for them
  const candidates = page.getByRole("button", { name: /^person \d+/i });
  await expect(candidates.first()).toBeVisible();
  expect(await candidates.count()).toBeGreaterThanOrEqual(2);
  await expect(page.getByRole("button", { name: "Continue" })).toBeDisabled();

  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expectNoHorizontalScroll(page);
  }

  await candidates.first().click();
  await expect(page.getByRole("button", { name: "Continue" })).toBeEnabled();
  await page.getByRole("button", { name: "Continue" }).click();

  await page.waitForURL(/\/studio\/results\//, { timeout: 5 * 60_000 });
  await expect(page.getByText("Overall score")).toBeVisible();
  const score = Number(await page.getByText(/^\d{1,3}\.\d$/).first().innerText());
  expect(score).toBeGreaterThanOrEqual(0);
  expect(score).toBeLessThanOrEqual(100);

  for (const width of [390, 768, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    await expectNoHorizontalScroll(page);
  }
  console.log(`duo clip -> picked a dancer -> real result rendered: score ${score} (${path.basename(dir)})`);
});
