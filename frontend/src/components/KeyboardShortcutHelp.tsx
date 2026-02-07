import { memo, useEffect } from "react";

interface KeyboardShortcutHelpProps {
  isOpen: boolean;
  onClose: () => void;
}

const SHORTCUTS = [
  { key: "/", description: "Focus search" },
  { key: "Esc", description: "Deselect node / clear search" },
  { key: "f", description: "Fit graph to screen" },
  { key: "[", description: "Navigate to incoming node" },
  { key: "]", description: "Navigate to outgoing node" },
  { key: "n", description: "Next search result" },
  { key: "N", description: "Previous search result" },
  { key: "1-5", description: "Toggle node type filter" },
  { key: "Alt+\u2190", description: "Breadcrumb back" },
  { key: "Alt+\u2192", description: "Breadcrumb forward" },
  { key: "?", description: "Toggle this help" },
  { key: "Ctrl+,", description: "Open settings" },
];

export const KeyboardShortcutHelp = memo(function KeyboardShortcutHelp({
  isOpen,
  onClose,
}: KeyboardShortcutHelpProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape" || e.key === "?") {
        e.preventDefault();
        e.stopPropagation();
        onClose();
      }
    };
    document.addEventListener("keydown", handleKeyDown, true);
    return () => document.removeEventListener("keydown", handleKeyDown, true);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
      <div
        className="bg-gray-800 border border-gray-700 rounded-lg shadow-xl p-6 max-w-md w-full mx-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-100">Keyboard Shortcuts</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-200">
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="grid grid-cols-[1fr_auto] gap-x-6 gap-y-2">
          {SHORTCUTS.map(({ key, description }) => (
            <div key={key} className="contents">
              <span className="text-sm text-gray-300">{description}</span>
              <kbd className="px-2 py-0.5 bg-gray-700 border border-gray-600 rounded text-xs text-gray-200 font-mono whitespace-nowrap">
                {key}
              </kbd>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
});
