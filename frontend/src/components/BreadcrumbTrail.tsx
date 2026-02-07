import { memo, useState, useRef, useEffect } from "react";
import type { NavigationEntry } from "../hooks/useNavigationHistory";

const NODE_COLORS: Record<string, string> = {
  class: "bg-blue-500",
  interface: "bg-purple-500",
  endpoint: "bg-green-500",
  package: "bg-gray-500",
  file: "bg-orange-500",
};

interface BreadcrumbTrailProps {
  entries: NavigationEntry[];
  cursor: number;
  canGoBack: boolean;
  canGoForward: boolean;
  onGoBack: () => void;
  onGoForward: () => void;
  onGoTo: (index: number) => void;
  onClear: () => void;
}

const MAX_VISIBLE = 5;

export const BreadcrumbTrail = memo(function BreadcrumbTrail({
  entries,
  cursor,
  canGoBack,
  canGoForward,
  onGoBack,
  onGoForward,
  onGoTo,
  onClear,
}: BreadcrumbTrailProps) {
  const [showOverflow, setShowOverflow] = useState(false);
  const overflowRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (overflowRef.current && !overflowRef.current.contains(e.target as Node)) {
        setShowOverflow(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  if (entries.length === 0) return null;

  const visibleStart = Math.max(0, entries.length - MAX_VISIBLE);
  const visibleEntries = entries.slice(visibleStart);
  const overflowEntries = entries.slice(0, visibleStart);
  const hasOverflow = overflowEntries.length > 0;

  return (
    <div className="h-8 bg-c-surface border-b border-c-line flex items-center px-3 gap-1 text-xs shrink-0">
      {/* Back button */}
      <button
        onClick={onGoBack}
        disabled={!canGoBack}
        className="p-1 text-c-text-dim hover:text-c-text disabled:opacity-30 disabled:cursor-default"
        title="Back (Alt+Left)"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Forward button */}
      <button
        onClick={onGoForward}
        disabled={!canGoForward}
        className="p-1 text-c-text-dim hover:text-c-text disabled:opacity-30 disabled:cursor-default"
        title="Forward (Alt+Right)"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      <span className="w-px h-4 bg-c-element mx-1" />

      {/* Overflow dropdown */}
      {hasOverflow && (
        <div className="relative" ref={overflowRef}>
          <button
            onClick={() => setShowOverflow(!showOverflow)}
            className="px-1.5 py-0.5 text-c-text-dim hover:text-c-text hover:bg-c-element rounded"
          >
            ...
          </button>
          {showOverflow && (
            <div className="absolute top-full left-0 mt-1 bg-c-surface border border-c-line rounded shadow-lg z-50 min-w-[160px]">
              {overflowEntries.map((entry, i) => (
                <button
                  key={i}
                  onClick={() => {
                    onGoTo(i);
                    setShowOverflow(false);
                  }}
                  className="w-full px-3 py-1.5 text-left text-xs hover:bg-c-element flex items-center gap-2"
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${NODE_COLORS[entry.type] || "bg-gray-500"}`} />
                  <span className="truncate text-c-text-sub">{entry.label}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Visible breadcrumbs */}
      {visibleEntries.map((entry, i) => {
        const actualIndex = visibleStart + i;
        const isCurrent = actualIndex === cursor;
        return (
          <button
            key={actualIndex}
            onClick={() => onGoTo(actualIndex)}
            className={`px-2 py-0.5 rounded flex items-center gap-1.5 max-w-[140px] ${
              isCurrent
                ? "bg-c-hover text-c-text"
                : "text-c-text-dim hover:text-c-text hover:bg-c-element"
            }`}
            title={entry.label}
          >
            <span className={`w-2 h-2 rounded-full shrink-0 ${NODE_COLORS[entry.type] || "bg-gray-500"}`} />
            <span className="truncate">{entry.label}</span>
          </button>
        );
      })}

      <div className="flex-1" />

      {/* Clear button */}
      <button
        onClick={onClear}
        className="p-1 text-c-text-faint hover:text-c-text-sub"
        title="Clear history"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>
  );
});
