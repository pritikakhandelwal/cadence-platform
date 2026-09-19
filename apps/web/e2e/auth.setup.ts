import { test as setup } from "@playwright/test";
import { registerAndOpenUpload } from "./helpers";

// Registers ONE user through the real form and saves the session for the
// "signed-in" project (registration is rate-limited, so tests share it).
setup("register the shared test user", async ({ page }) => {
  await registerAndOpenUpload(page);
  await page.context().storageState({ path: "e2e/.auth/user.json" });
});
