import { defineConfig, devices } from "@playwright/test";

// The tests log in like a person does, with the Basic Auth values proxy.ts checks
try {
  process.loadEnvFile(".env.local");
} catch {
  // No .env.local: every page answers 401, and the tests say so
}

export default defineConfig({
  testDir: "./e2e",
  use: {
    baseURL: "http://localhost:3000",
    httpCredentials: { username: process.env.BASIC_AUTH_USER ?? "", password: process.env.BASIC_AUTH_PASSWORD ?? "" },
    trace: "retain-on-failure",
  },
  // The installed Edge, so `npx playwright install` isn't needed. Phone width checks the tab bar layout.
  projects: [
    { name: "desktop", use: { ...devices["Desktop Edge"], channel: "msedge" } },
    { name: "phone", use: { ...devices["Pixel 7"], channel: "msedge" } },
  ],
  // Reuses `npm run dev` if it's already running, otherwise starts it
  webServer: { command: "npm run dev", url: "http://localhost:3000", reuseExistingServer: true },
});
