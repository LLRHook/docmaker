import { test, expect } from "@playwright/test";

test.describe("App smoke tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("app loads and shows header", async ({ page }) => {
    await expect(page.locator("h1")).toHaveText("Docmaker");
  });

  test("shows Dev Mode badge when Pyloid is unavailable", async ({ page }) => {
    await expect(page.getByText("Dev Mode")).toBeVisible();
  });

  test("Open Project button is visible", async ({ page }) => {
    await expect(page.getByRole("button", { name: /Open Project/i })).toBeVisible();
  });

  test("Open Project dropdown shows browse and path options", async ({ page }) => {
    await page.getByRole("button", { name: /Open Project/i }).click();
    await expect(page.getByText("Browse...")).toBeVisible();
    await expect(page.getByText("Enter path...")).toBeVisible();
  });

  test("Enter path modal opens and closes", async ({ page }) => {
    await page.getByRole("button", { name: /Open Project/i }).click();
    await page.getByText("Enter path...").click();
    await expect(page.getByPlaceholder(/path/i)).toBeVisible();

    // Close with Escape
    await page.keyboard.press("Escape");
    await expect(page.getByPlaceholder(/path/i)).not.toBeVisible();
  });

  test("Settings modal opens via button", async ({ page }) => {
    await page.getByTitle("Settings (Ctrl+,)").click();
    await expect(page.getByRole("heading", { name: "Settings" })).toBeVisible();
  });

  test("Settings modal closes with Escape", async ({ page }) => {
    await page.getByTitle("Settings (Ctrl+,)").click();
    const heading = page.getByRole("heading", { name: "Settings" });
    await expect(heading).toBeVisible();

    await page.keyboard.press("Escape");
    await expect(heading).not.toBeVisible();
  });

  test("empty graph shows placeholder", async ({ page }) => {
    await expect(page.getByText("No nodes to display")).toBeVisible();
  });

  test("status bar is visible", async ({ page }) => {
    await expect(page.getByTestId("status-message")).toHaveText("Ready");
  });
});
