import { test } from "@playwright/test";
import { expectNoHorizontalScroll, openUpload } from "./helpers";

// No page may scroll sideways at phone, tablet or desktop width. (The pick and
// results pages are checked inside flows.spec.ts, where a real analysis exists.)
const WIDTHS = [
  { name: "phone", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
];

for (const { name, width, height } of WIDTHS) {
  test.describe(`${name} (${width}px)`, () => {
    test.use({ viewport: { width, height } });

    test.describe("public pages, logged out", () => {
      test.use({ storageState: { cookies: [], origins: [] } });

      for (const route of ["/", "/login", "/register"]) {
        test(`${route} fits`, async ({ page }) => {
          await page.goto(route);
          await expectNoHorizontalScroll(page);
        });
      }
    });

    test("/studio/upload fits, in both reference modes", async ({ page }) => {
      await openUpload(page);
      await expectNoHorizontalScroll(page);
      await page.getByRole("button", { name: /paste youtube link/i }).click();
      await expectNoHorizontalScroll(page);
    });
  });
}
