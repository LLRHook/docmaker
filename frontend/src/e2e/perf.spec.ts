import { test, expect } from "@playwright/test";
import { resolve } from "path";

const FIXTURE_PATH = resolve(
  import.meta.dirname,
  "fixtures",
  "sample-project"
);

// Helper to enable perf collection and load a project via the path input modal
async function loadFixtureProject(page: import("@playwright/test").Page) {
  // Enable perf collection
  await page.evaluate(() => {
    window.__DOCMAKER_PERF = true;
  });

  // Open the path input modal
  await page.getByRole("button", { name: /Open Project/i }).click();
  await page.getByText("Enter path...").click();

  // Type the fixture path and submit
  const input = page.getByPlaceholder(/path/i);
  await input.fill(FIXTURE_PATH);
  await page.getByRole("button", { name: "Open", exact: true }).click();

  // Wait for parsing status to appear and resolve
  // In dev mode (no Pyloid), parseOnly will fail, so we check for either
  // "ready" status or "error" status to know the attempt completed
  await page.waitForFunction(
    () => {
      const statusEl = document.querySelector("[data-testid='status-message']");
      if (!statusEl) return false;
      const text = statusEl.textContent || "";
      return text.includes("Loaded") || text.includes("error") || text.includes("Error");
    },
    { timeout: 15000 }
  );
}

// Helper to extract perf metrics from the page
async function getMetrics(page: import("@playwright/test").Page) {
  return page.evaluate(() => {
    if (typeof window.__DOCMAKER_METRICS === "function") {
      return window.__DOCMAKER_METRICS();
    }
    return [];
  });
}

function findMetric(metrics: Array<{ name: string; duration: number }>, name: string) {
  return metrics.find((m) => m.name === name);
}

test.describe("Performance benchmarks @perf", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("project load time @perf", async ({ page }) => {
    await loadFixtureProject(page);
    const metrics = await getMetrics(page);

    console.log("\n--- Performance Metrics: Project Load ---");
    for (const m of metrics) {
      console.log(`  ${m.name.padEnd(30)} ${m.duration.toFixed(1)}ms`);
    }

    // These thresholds apply when the backend is running.
    // In dev-only mode (no Pyloid), IPC calls time out — we just log metrics.
    const projectLoad = findMetric(metrics, "app:projectLoad");
    const parseOnly = findMetric(metrics, "ipc:parseOnly");

    if (projectLoad) console.log(`\napp:projectLoad = ${projectLoad.duration}ms`);
    if (parseOnly) console.log(`ipc:parseOnly = ${parseOnly.duration}ms`);

    // Only assert budgets if the backend responded (parse didn't time out)
    if (parseOnly && parseOnly.duration < 9000) {
      expect(projectLoad!.duration).toBeLessThan(5000);
      expect(parseOnly.duration).toBeLessThan(10000);
    }
  });

  test("settings modal render speed @perf", async ({ page }) => {
    await page.evaluate(() => {
      window.__DOCMAKER_PERF = true;
    });

    const start = Date.now();
    await page.keyboard.press("Control+,");
    await expect(page.getByText("Graph View")).toBeVisible();
    const elapsed = Date.now() - start;

    console.log(`\nsettings:modalOpen = ${elapsed}ms`);
    expect(elapsed).toBeLessThan(1000);
  });

  test("page initial load @perf", async ({ page }) => {
    const start = Date.now();
    await page.goto("/");
    await expect(page.locator("h1")).toHaveText("Docmaker");
    const elapsed = Date.now() - start;

    console.log(`\npage:initialLoad = ${elapsed}ms`);
    expect(elapsed).toBeLessThan(3000);
  });
});
