import { expect, test } from "@playwright/test";

// These only touch pages that work without the backend, so they need no API keys and cost nothing

test("the sidebar switches pages and marks the current one", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Process a receipt" })).toBeVisible();

  await page.getByRole("link", { name: "Ask a question" }).click();
  await expect(page.getByRole("heading", { name: "Ask a question" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Ask a question" })).toHaveAttribute("aria-current", "page");
});

test("an unsupported file pops up an error and uploads nothing", async ({ page }) => {
  const uploads: string[] = [];
  page.on("request", (request) => {
    if (request.url().endsWith("/api/receipts")) uploads.push(request.url());
  });
  await page.goto("/");

  await page.locator("#receipt-photo").setInputFiles({ name: "notes.txt", mimeType: "text/plain", buffer: Buffer.from("not a photo") });

  // Next.js has its own hidden role="alert" element for screen readers, so match on the text
  await expect(page.getByRole("alert").filter({ hasText: "isn't a supported format" })).toBeVisible();
  expect(uploads).toEqual([]);
});

test("the ask button waits for a question", async ({ page }) => {
  await page.goto("/ask");
  const ask = page.getByRole("button", { name: "Ask" });

  await expect(ask).toBeDisabled();
  await page.getByLabel("Question").fill("Restaurant fundraisers near campus");
  await expect(ask).toBeEnabled();
});
