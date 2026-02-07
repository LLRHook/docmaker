declare global {
  interface Window {
    __DOCMAKER_PERF?: boolean;
    __DOCMAKER_METRICS: () => PerfEntry[];
  }
}

interface PerfEntry {
  name: string;
  duration: number;
  startTime: number;
}

function isEnabled(): boolean {
  return window.__DOCMAKER_PERF === true;
}

export function markStart(name: string): void {
  if (!isEnabled()) return;
  performance.mark(`${name}:start`);
}

export function markEnd(name: string): void {
  if (!isEnabled()) return;
  const startMark = `${name}:start`;
  const endMark = `${name}:end`;
  performance.mark(endMark);
  try {
    performance.measure(name, startMark, endMark);
  } catch {
    // start mark may not exist if perf was enabled mid-flow
  }
}

export function getMetrics(): PerfEntry[] {
  return performance.getEntriesByType("measure").map((entry) => ({
    name: entry.name,
    duration: Math.round(entry.duration * 100) / 100,
    startTime: Math.round(entry.startTime * 100) / 100,
  }));
}

export function clearMetrics(): void {
  performance.clearMarks();
  performance.clearMeasures();
}

// Expose globally for Playwright extraction
window.__DOCMAKER_METRICS = getMetrics;
