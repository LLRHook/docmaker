import { readdirSync, statSync } from "fs";
import { join } from "path";

const BUDGETS = {
  js: 900 * 1024,  // 900 KB
  css: 50 * 1024,  // 50 KB
  total: 1024 * 1024, // 1 MB
};

const assetsDir = join(import.meta.dirname, "..", "dist", "assets");

let jsTotal = 0;
let cssTotal = 0;
let totalSize = 0;
const files = [];

try {
  for (const file of readdirSync(assetsDir)) {
    const size = statSync(join(assetsDir, file)).size;
    totalSize += size;
    files.push({ file, size });

    if (file.endsWith(".js")) jsTotal += size;
    else if (file.endsWith(".css")) cssTotal += size;
  }
} catch {
  console.error("No dist/assets directory found. Run `npm run build` first.");
  process.exit(1);
}

const fmt = (bytes) => `${(bytes / 1024).toFixed(1)} KB`;

console.log("\nBundle Size Report");
console.log("==================");
files
  .sort((a, b) => b.size - a.size)
  .forEach(({ file, size }) => console.log(`  ${file.padEnd(40)} ${fmt(size)}`));

console.log(`\n  JS total:   ${fmt(jsTotal).padStart(10)}  (budget: ${fmt(BUDGETS.js)})`);
console.log(`  CSS total:  ${fmt(cssTotal).padStart(10)}  (budget: ${fmt(BUDGETS.css)})`);
console.log(`  Total:      ${fmt(totalSize).padStart(10)}  (budget: ${fmt(BUDGETS.total)})`);

let failed = false;
if (jsTotal > BUDGETS.js) { console.error(`\n  FAIL: JS bundle exceeds budget by ${fmt(jsTotal - BUDGETS.js)}`); failed = true; }
if (cssTotal > BUDGETS.css) { console.error(`\n  FAIL: CSS bundle exceeds budget by ${fmt(cssTotal - BUDGETS.css)}`); failed = true; }
if (totalSize > BUDGETS.total) { console.error(`\n  FAIL: Total exceeds budget by ${fmt(totalSize - BUDGETS.total)}`); failed = true; }

if (failed) {
  console.log("\n  Result: FAIL\n");
  process.exit(1);
} else {
  console.log("\n  Result: PASS\n");
}
