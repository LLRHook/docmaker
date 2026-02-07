import { useRef, useCallback, useEffect } from "react";
import type { ElementDefinition } from "cytoscape";
import type { LayoutResponse } from "../workers/layout.worker";

export function useLayoutWorker() {
  const workerRef = useRef<Worker | null>(null);

  const terminate = useCallback(() => {
    if (workerRef.current) {
      workerRef.current.terminate();
      workerRef.current = null;
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => terminate, [terminate]);

  const computeLayout = useCallback(
    (
      elements: ElementDefinition[],
      options: Record<string, unknown>,
    ): Promise<LayoutResponse> => {
      // Terminate any in-flight worker
      terminate();

      return new Promise((resolve, reject) => {
        const worker = new Worker(
          new URL("../workers/layout.worker.ts", import.meta.url),
          { type: "module" },
        );
        workerRef.current = worker;

        worker.onmessage = (e: MessageEvent<LayoutResponse>) => {
          resolve(e.data);
          worker.terminate();
          workerRef.current = null;
        };

        worker.onerror = (err) => {
          reject(err);
          worker.terminate();
          workerRef.current = null;
        };

        worker.postMessage({ elements, options });
      });
    },
    [terminate],
  );

  return { computeLayout, terminate };
}
