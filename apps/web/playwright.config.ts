import { defineConfig } from "@playwright/test";

// Local end-to-end tests: a real browser against a REAL running stack (see
// e2e/README.md). Not run in CI -- they need apps/api, Redis and (for the
// full-pipeline spec) apps/worker with its ML dependencies and real videos.
// Drives an already-installed Edge by default so no browser is downloaded;
// set CADENCE_E2E_CHANNEL=chrome (or unset it via a bundled browser) to change.
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
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: true,
    timeout: 120_000,
  },
});
