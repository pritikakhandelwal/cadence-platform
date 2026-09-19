import { expect, test } from "@playwright/test";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const PASSWORD = "correct-horse-battery";

function uniqueEmail() {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1e6)}@example.com`;
}

test("the studio is gated: a logged-out visitor is sent to log in", async ({ page }) => {
  await page.goto("/studio/upload");

  await expect(page).toHaveURL(/\/login\?next=(%2F|\/)studio(%2F|\/)upload/);
  await expect(page.getByRole("button", { name: "Log in" })).toBeVisible();
});

test("registering creates the account, signs in, and lands in the studio", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Tester");
  await page.getByLabel("Email").fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page).toHaveURL(/\/studio\/upload/);
  await expect(page.getByText("Add your two videos")).toBeVisible();
});

test("a wrong password is refused with the server's reason; the right one gets back to the page they wanted", async ({
  page,
  request,
}) => {
  const email = uniqueEmail();
  const registered = await request.post(`${API}/auth/register`, {
    data: { name: "E2E Tester", email, password: PASSWORD, confirm: PASSWORD },
  });
  expect(registered.ok()).toBeTruthy();

  await page.goto("/login?next=/studio/upload");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Password").fill("not-the-password");
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page.locator("form").getByText(/incorrect|invalid|wrong/i)).toBeVisible();
  await expect(page).toHaveURL(/\/login/);

  await page.getByLabel("Password").fill(PASSWORD);
  await page.getByRole("button", { name: "Log in" }).click();
  await expect(page).toHaveURL(/\/studio\/upload/);
});

test("the upload form refuses to continue until both videos are supplied", async ({ page }) => {
  await page.goto("/register");
  await page.getByLabel("Name").fill("E2E Tester");
  await page.getByLabel("Email").fill(uniqueEmail());
  await page.getByLabel("Password", { exact: true }).fill(PASSWORD);
  await page.getByLabel("Confirm password").fill(PASSWORD);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(page.getByText("Add your two videos")).toBeVisible();

  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Add your practice video first.")).toBeVisible();
  await expect(page).toHaveURL(/\/studio\/upload/);
});
