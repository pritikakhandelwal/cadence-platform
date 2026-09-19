import { expect, test } from "@playwright/test";
import { openUpload } from "./helpers";

test("the upload form refuses to continue until both videos are supplied", async ({ page }) => {
  await openUpload(page);

  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByText("Add your practice video first.")).toBeVisible();
  await expect(page).toHaveURL(/\/studio\/upload/);
});
