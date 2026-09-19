import path from "node:path";
import { expect, test } from "@playwright/test";

const USER_VIDEO = process.env.CADENCE_E2E_USER_VIDEO;
const REFERENCE_VIDEO = process.env.CADENCE_E2E_REFERENCE_VIDEO;

test.skip(
  !USER_VIDEO || !REFERENCE_VIDEO,
  "set CADENCE_E2E_USER_VIDEO and CADENCE_E2E_REFERENCE_VIDEO to two real solo dance clips (see e2e/README.md)"
);

test("upload two real clips through the real form and watch a real result appear", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Tester");
  await page.getByLabel("Email").fill(`e2e-${Date.now()}@example.com`);
  await page.getByLabel("Password", { exact: true }).fill("correct-horse-battery");
  await page.getByLabel("Confirm password").fill("correct-horse-battery");
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Add your two videos")).toBeVisible();

  // The real <input type="file"> elements -- the part no other check could drive.
  const inputs = page.locator('input[type="file"]');
  await inputs.nth(0).setInputFiles(USER_VIDEO!);
  await inputs.nth(1).setInputFiles(REFERENCE_VIDEO!);
  await expect(page.getByText(path.basename(USER_VIDEO!))).toBeVisible();
  await expect(page.getByText(path.basename(REFERENCE_VIDEO!))).toBeVisible();

  await page.getByRole("button", { name: "Continue" }).click();
  await page.waitForURL(/\/studio\/processing\//);
  await expect(page.getByText("Analyzing your performance")).toBeVisible();

  // The page polls the real API and routes itself. If the lock is ambiguous
  // (more than one comparably-sized person) it lands on the pick page first.
  await page.waitForURL(/\/studio\/(results|pick)\//, { timeout: 5 * 60_000 });
  if (page.url().includes("/studio/pick/")) {
    await page.getByRole("button", { name: /person/i }).first().click();
    await page.getByRole("button", { name: "Continue" }).click();
    await page.waitForURL(/\/studio\/results\//, { timeout: 5 * 60_000 });
  }

  await expect(page.getByText("Overall score")).toBeVisible();
  const score = await page.getByText(/^\d{1,3}\.\d$/).first().innerText();
  expect(Number(score)).toBeGreaterThanOrEqual(0);
  expect(Number(score)).toBeLessThanOrEqual(100);
  await expect(page.getByText("angle-dtw-v2 · v2")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Timeline" })).toBeVisible();
  console.log(`real result rendered in the browser: score ${score}`);
});
