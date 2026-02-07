import { useEffect } from "react";

export interface KeyboardNavigationCallbacks {
  focusSearch: () => void;
  clearSearch: () => void;
  deselectNode: () => void;
  fitGraph: () => void;
  navigateConnected: (direction: "incoming" | "outgoing") => void;
  nextSearchResult: () => void;
  prevSearchResult: () => void;
  toggleNodeType: (index: number) => void;
  goBack: () => void;
  goForward: () => void;
  toggleHelp: () => void;
}

export function useKeyboardNavigation(callbacks: KeyboardNavigationCallbacks) {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      const isInput = target.tagName === "INPUT" || target.tagName === "TEXTAREA" || target.isContentEditable;

      // Escape always works
      if (e.key === "Escape") {
        if (isInput) {
          (target as HTMLInputElement).blur();
        }
        callbacks.clearSearch();
        callbacks.deselectNode();
        return;
      }

      // Alt+Arrow keys work regardless of focus
      if (e.altKey && e.key === "ArrowLeft") {
        e.preventDefault();
        callbacks.goBack();
        return;
      }
      if (e.altKey && e.key === "ArrowRight") {
        e.preventDefault();
        callbacks.goForward();
        return;
      }

      // Ignore other shortcuts when input is focused
      if (isInput) return;

      switch (e.key) {
        case "/":
          e.preventDefault();
          callbacks.focusSearch();
          break;
        case "f":
          callbacks.fitGraph();
          break;
        case "[":
          callbacks.navigateConnected("incoming");
          break;
        case "]":
          callbacks.navigateConnected("outgoing");
          break;
        case "n":
          callbacks.nextSearchResult();
          break;
        case "N":
          callbacks.prevSearchResult();
          break;
        case "1":
        case "2":
        case "3":
        case "4":
        case "5":
          callbacks.toggleNodeType(parseInt(e.key) - 1);
          break;
        case "?":
          callbacks.toggleHelp();
          break;
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [callbacks]);
}
