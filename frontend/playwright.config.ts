import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e/specs",
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: [["html", { open: "never" }], ["list"]],
  use: {
    baseURL: "http://localhost:3100",
    headless: true,
    screenshot: "on",
    trace: "retain-on-failure",
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: "setup",
      testMatch: /01-connection\.spec\.ts/,
    },
    {
      name: "features",
      testMatch: /0[2-9]-.*\.spec\.ts|1[0-1]-.*\.spec\.ts/,
      dependencies: ["setup"],
    },
    {
      name: "k8s",
      testMatch: /k8s-.*\.spec\.ts/,
    },
  ],
  globalSetup: "./e2e/global-setup.ts",
  globalTeardown: "./e2e/global-teardown.ts",
  outputDir: "./e2e/test-results",
});
