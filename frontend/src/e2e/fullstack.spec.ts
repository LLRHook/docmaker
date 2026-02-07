import { test, expect, type Page } from "@playwright/test";
import { spawn, type ChildProcess } from "child_process";
import { resolve } from "path";

const BRIDGE_PORT = 8765;
const BRIDGE_URL = `http://127.0.0.1:${BRIDGE_PORT}`;
const PROJECT_PATH =
  process.env.DOCMAKER_E2E_PROJECT || "C:\\Users\\victo\\git\\knock";

// Path to the bridge server script (relative to repo root)
const BRIDGE_SCRIPT = resolve(
  import.meta.dirname,
  "..",
  "..",
  "..",
  "tests",
  "e2e",
  "bridge_server.py"
);

let bridgeProcess: ChildProcess;

test.beforeAll(async () => {
  bridgeProcess = spawn("python", [BRIDGE_SCRIPT, String(BRIDGE_PORT)], {
    stdio: ["ignore", "pipe", "pipe"],
  });

  // Wait for "Bridge server ready" on stdout
  await new Promise<void>((resolve, reject) => {
    const timeout = setTimeout(
      () => reject(new Error("Bridge server did not start within 10s")),
      10_000
    );

    bridgeProcess.stdout!.on("data", (chunk: Buffer) => {
      const text = chunk.toString();
      if (text.includes("Bridge server ready")) {
        clearTimeout(timeout);
        resolve();
      }
    });

    bridgeProcess.stderr!.on("data", (chunk: Buffer) => {
      console.error("[bridge stderr]", chunk.toString());
    });

    bridgeProcess.on("error", (err) => {
      clearTimeout(timeout);
      reject(err);
    });

    bridgeProcess.on("exit", (code) => {
      clearTimeout(timeout);
      if (code !== null && code !== 0) {
        reject(new Error(`Bridge server exited with code ${code}`));
      }
    });
  });
});

test.afterAll(async () => {
  if (bridgeProcess && !bridgeProcess.killed) {
    bridgeProcess.kill();
  }
});

/**
 * Inject a fake window.__PYLOID__ + window.ipc that proxies IPC calls
 * to the bridge HTTP server. This makes pyloid-js think Pyloid is running.
 */
function bridgeInitScript(bridgeUrl: string): string {
  return `
    window.__PYLOID__ = {};
    window.ipc = {
      DocmakerAPI: new Proxy({}, {
        get(_target, method) {
          return async function(...args) {
            const resp = await fetch("${bridgeUrl}/ipc/" + method, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ args }),
            });
            return resp.text();
          };
        },
      }),
    };
  `;
}

async function setupPage(page: Page) {
  await page.addInitScript(bridgeInitScript(BRIDGE_URL));
  await page.goto("/");
  // Wait for Pyloid ready state (pyloid-js polls for window.__PYLOID__)
  await page.waitForFunction(() => !!window.__PYLOID__, { timeout: 5000 });
}

async function loadProject(page: Page) {
  await page.getByRole("button", { name: /Open Project/i }).click();
  await page.getByText("Enter path...").click();

  const input = page.getByPlaceholder(/path/i);
  await input.fill(PROJECT_PATH);
  await page.getByRole("button", { name: "Open", exact: true }).click();

  // Wait for load to complete (success or error)
  await page.waitForFunction(
    () => {
      const el = document.querySelector("[data-testid='status-message']");
      if (!el) return false;
      const text = el.textContent || "";
      return text.includes("Loaded") || text.includes("error") || text.includes("Error");
    },
    { timeout: 120_000 }
  );
}

async function getMetrics(page: Page) {
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

/**
 * Extract class and endpoint counts from the sidebar group headers.
 * Headers render as "Classes (N)" and "Endpoints (N)".
 */
async function getSidebarGroupCount(page: Page, groupLabel: string): Promise<number> {
  const header = page.locator("button", { hasText: new RegExp(`${groupLabel}\\s*\\(\\d+\\)`) });
  const count = await header.count();
  if (count === 0) return 0;
  const text = await header.first().textContent();
  const match = text?.match(/\((\d+)\)/);
  return match ? parseInt(match[1], 10) : 0;
}

// ---------- Tests ----------

test.describe("Full-stack E2E with real project", () => {
  test.beforeEach(async ({ page }) => {
    await setupPage(page);
  });

  test("parses real project and renders graph", async ({ page }) => {
    await loadProject(page);

    // Status should show class/endpoint counts
    const statusText = await page
      .getByTestId("status-message")
      .textContent();
    expect(statusText).toContain("Loaded");
    expect(statusText).toMatch(/\d+\s+class/i);

    // Graph area should have rendered Cytoscape (canvas element present)
    // The graph view is the div.flex-1.relative.bg-gray-900
    const graphArea = page.locator(".flex-1.relative.bg-gray-900");
    await expect(graphArea).toBeVisible();

    // "No nodes to display" placeholder should NOT be visible
    await expect(page.getByText("No nodes to display")).not.toBeVisible();
  });

  test("parse performance within budget @perf @fullstack", async ({ page }) => {
    // Enable perf collection before navigating
    await page.evaluate(() => {
      window.__DOCMAKER_PERF = true;
    });

    // Re-navigate with perf enabled
    await page.goto("/");
    await page.waitForFunction(() => !!window.__PYLOID__, { timeout: 5000 });

    await loadProject(page);

    const metrics = await getMetrics(page);

    console.log("\n--- Full-Stack Performance Metrics ---");
    for (const m of metrics) {
      console.log(`  ${m.name.padEnd(30)} ${m.duration.toFixed(1)}ms`);
    }

    const parseOnly = findMetric(metrics, "ipc:parseOnly");
    const projectLoad = findMetric(metrics, "app:projectLoad");

    if (parseOnly) console.log(`\nipc:parseOnly = ${parseOnly.duration}ms`);
    if (projectLoad) console.log(`app:projectLoad = ${projectLoad.duration}ms`);

    // Real project budgets (507 Java files)
    if (parseOnly) {
      expect(parseOnly.duration).toBeLessThan(30_000);
    }
    if (projectLoad) {
      expect(projectLoad.duration).toBeLessThan(35_000);
    }
  });

  test("sidebar shows real class and endpoint nodes", async ({ page }) => {
    await loadProject(page);

    // Sidebar stats footer shows "Showing X of Y nodes"
    const statsText = await page.getByText(/Showing \d+ of \d+ nodes/).textContent();
    console.log(`Sidebar stats: ${statsText}`);
    const totalMatch = statsText?.match(/of (\d+) nodes/);
    const totalNodes = totalMatch ? parseInt(totalMatch[1], 10) : 0;
    expect(totalNodes).toBeGreaterThan(100);

    // Check group headers for class and endpoint counts
    const classCount = await getSidebarGroupCount(page, "Classes");
    console.log(`Sidebar class nodes: ${classCount}`);
    expect(classCount).toBeGreaterThan(100);

    const endpointCount = await getSidebarGroupCount(page, "Endpoints");
    console.log(`Sidebar endpoint nodes: ${endpointCount}`);
    expect(endpointCount).toBeGreaterThan(0);
  });

  test("class details panel populates with real data", async ({ page }) => {
    await loadProject(page);

    // Find the Classes group header and ensure it's expanded
    const classesHeader = page.locator("button", { hasText: /Classes\s*\(\d+\)/ }).first();
    await expect(classesHeader).toBeVisible({ timeout: 5000 });

    // The group content (list of class buttons) follows the header
    // Each class node button is inside div.max-h-48 following the group header
    // Click the first class node button in the list
    const classGroup = classesHeader.locator(".."); // parent div
    const classNodeButtons = classGroup.locator("div.max-h-48 button");
    const nodeCount = await classNodeButtons.count();
    expect(nodeCount).toBeGreaterThan(0);

    await classNodeButtons.first().click();

    // Details panel should show the "Methods" section for a class
    // The details panel is on the right side with border-l border-gray-700
    const methodsSection = page.getByText(/Methods\s*\(\d+\)/i);
    await expect(methodsSection).toBeVisible({ timeout: 10_000 });

    // Should also show Overview section with type info
    await expect(page.getByText("Overview")).toBeVisible();
  });

  test("endpoint details panel populates with real data", async ({ page }) => {
    await loadProject(page);

    // Find and expand the Endpoints group
    const endpointsHeader = page.locator("button", { hasText: /Endpoints\s*\(\d+\)/ }).first();
    await expect(endpointsHeader).toBeVisible({ timeout: 5000 });

    // Click the first endpoint node
    const endpointGroup = endpointsHeader.locator("..");
    const endpointButtons = endpointGroup.locator("div.max-h-48 button");
    const nodeCount = await endpointButtons.count();
    expect(nodeCount).toBeGreaterThan(0);

    await endpointButtons.first().click();

    // Should show Handler section (endpoint-specific)
    // Use heading role to avoid matching sidebar buttons that contain "Handler"
    await expect(page.locator("h3", { hasText: /^Handler$/i })).toBeVisible({ timeout: 10_000 });

    // The endpoint banner should contain an HTTP method badge
    const methodBadge = page.locator("span", { hasText: /^(GET|POST|PUT|DELETE|PATCH)$/ });
    await expect(methodBadge.first()).toBeVisible();
  });
});
