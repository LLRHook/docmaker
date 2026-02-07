import { useState, useCallback } from "react";
import type { SourceSnippet } from "../types/graph";
import { usePyloid } from "../hooks/usePyloid";

interface SourcePreviewProps {
  filePath: string;
  startLine: number;
  endLine: number;
  label: string;
}

export function SourcePreview({ filePath, startLine, endLine, label }: SourcePreviewProps) {
  const [expanded, setExpanded] = useState(false);
  const [snippet, setSnippet] = useState<SourceSnippet | null>(null);
  const [loading, setLoading] = useState(false);
  const { getSourceSnippet, isAvailable } = usePyloid();

  const handleToggle = useCallback(async () => {
    if (expanded) {
      setExpanded(false);
      return;
    }

    setExpanded(true);

    if (snippet) return;

    setLoading(true);
    try {
      if (isAvailable()) {
        const result = await getSourceSnippet(filePath, startLine, endLine);
        if (!result.error) {
          setSnippet(result);
        } else {
          setSnippet({ lines: [`// Could not load source: ${result.error}`], startLine, endLine, totalLines: 0, path: filePath });
        }
      } else {
        // Dev mode fallback: show placeholder
        setSnippet({
          lines: [`// Source: ${filePath}:${startLine}-${endLine}`, "// (Preview unavailable in dev mode)"],
          startLine,
          endLine,
          totalLines: 0,
          path: filePath,
        });
      }
    } catch {
      setSnippet({
        lines: ["// Error loading source"],
        startLine,
        endLine,
        totalLines: 0,
        path: filePath,
      });
    } finally {
      setLoading(false);
    }
  }, [expanded, snippet, filePath, startLine, endLine, getSourceSnippet, isAvailable]);

  return (
    <div className="mt-1">
      <button
        onClick={handleToggle}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
        title={`${expanded ? "Hide" : "Show"} source for ${label}`}
      >
        <svg
          className={`w-3 h-3 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
        <span>Source</span>
      </button>

      {expanded && (
        <div className="mt-1 rounded border border-gray-700 bg-gray-900 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-3">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : snippet ? (
            <div className="overflow-x-auto">
              <pre className="text-xs leading-relaxed">
                {snippet.lines.map((line, i) => {
                  const lineNum = snippet.startLine + i;
                  return (
                    <div key={lineNum} className="flex hover:bg-gray-800/50">
                      <span className="select-none text-gray-600 text-right w-10 pr-2 shrink-0 border-r border-gray-700/50">
                        {lineNum}
                      </span>
                      <span className="text-gray-300 pl-2 whitespace-pre">{line}</span>
                    </div>
                  );
                })}
              </pre>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}
