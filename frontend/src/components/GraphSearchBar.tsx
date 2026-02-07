import { forwardRef, useCallback } from "react";

interface GraphSearchBarProps {
  query: string;
  matchCount: number;
  activeIndex: number;
  onChange: (query: string) => void;
  onNext: () => void;
  onPrev: () => void;
  onClear: () => void;
  onSelectActive: () => void;
}

export const GraphSearchBar = forwardRef<HTMLInputElement, GraphSearchBarProps>(
  function GraphSearchBar({ query, matchCount, activeIndex, onChange, onNext, onPrev, onClear, onSelectActive }, ref) {
    const handleKeyDown = useCallback(
      (e: React.KeyboardEvent<HTMLInputElement>) => {
        if (e.key === "Enter") {
          e.preventDefault();
          if (e.shiftKey) {
            onPrev();
          } else {
            onNext();
          }
        } else if (e.key === "Escape") {
          e.preventDefault();
          onClear();
          (e.target as HTMLInputElement).blur();
        } else if (e.key === "Tab") {
          e.preventDefault();
          onSelectActive();
        }
      },
      [onNext, onPrev, onClear, onSelectActive]
    );

    return (
      <div className="bg-gray-800 rounded-lg shadow-lg flex items-center px-2 gap-1">
        <svg className="w-4 h-4 text-gray-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          ref={ref}
          type="text"
          value={query}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Search graph... (@ann, type:, modifier)"
          className="bg-transparent border-none text-sm text-gray-100 placeholder-gray-500 focus:outline-none w-48 py-2"
        />
        {query && (
          <>
            <span className="text-xs text-gray-400 whitespace-nowrap">
              {matchCount > 0 ? `${activeIndex + 1}/${matchCount}` : "0 results"}
            </span>
            <button
              onClick={onPrev}
              className="p-1 text-gray-400 hover:text-gray-200"
              title="Previous match (Shift+Enter)"
              disabled={matchCount === 0}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 15l7-7 7 7" />
              </svg>
            </button>
            <button
              onClick={onNext}
              className="p-1 text-gray-400 hover:text-gray-200"
              title="Next match (Enter)"
              disabled={matchCount === 0}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
            <button
              onClick={onClear}
              className="p-1 text-gray-400 hover:text-gray-200"
              title="Clear search (Escape)"
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </>
        )}
      </div>
    );
  }
);
