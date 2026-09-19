import { defineConfig } from "@playwright/test";

// Local end-to-end tests: a real browser against a REAL running stack (see
// e2e/README.md). Not run in CI -- they need apps/api, Redis and (for the
// flow specs) apps/worker with its ML dependencies and real videos.
// Drives an already-installed Edge by default so no browser is downloaded;
// set CADENCE_E2E_CHANNEL=chrome to use Chrome instead.
//
// The API rate-limits registration (5 per hour per IP), so tests don't register
// a user each: one "setup" test registers a shared user and saves its session,
// and the "signed-in" project reuses it. Only auth.spec.ts starts logged out.
export default defineConfig({
  testDir: "./e2e",
  timeout: 6 * 60_000,
  workers: 1,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    channel: process.env.CADENCE_E2E_CHANNEL ?? "msedge",
    trace: "retain-on-failure",
  },
  projects: [
    { name: "setup", testMatch: /auth\.setup\.ts/ },
    { name: "anonymous", testMatch: /auth\.spec\.ts/ },
    {
      name: "signed-in",
      testIgnore: [/auth\.setup\.ts/, /auth\.spec\.ts/],
      dependencies: ["setup"],
      use: { storageState: "e2e/.auth/user.json" },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
