import { useState, useCallback, useRef } from "react";

export interface NavigationEntry {
  nodeId: string;
  label: string;
  type: string;
}

interface NavigationHistory {
  entries: NavigationEntry[];
  cursor: number;
  canGoBack: boolean;
  canGoForward: boolean;
  push: (entry: NavigationEntry) => void;
  goBack: () => NavigationEntry | null;
  goForward: () => NavigationEntry | null;
  goTo: (index: number) => NavigationEntry | null;
  clear: () => void;
  skipNextPush: () => void;
}

const MAX_ENTRIES = 10;

export function useNavigationHistory(): NavigationHistory {
  const [entries, setEntries] = useState<NavigationEntry[]>([]);
  const [cursor, setCursor] = useState(-1);
  const skipNextPushRef = useRef(false);

  const push = useCallback((entry: NavigationEntry) => {
    if (skipNextPushRef.current) {
      skipNextPushRef.current = false;
      return;
    }
    setEntries((prev) => {
      // Remove forward history when pushing from middle
      const trimmed = prev.slice(0, cursor + 1);
      // Don't push duplicate of current entry
      if (trimmed.length > 0 && trimmed[trimmed.length - 1].nodeId === entry.nodeId) {
        return trimmed;
      }
      const next = [...trimmed, entry];
      // Cap at MAX_ENTRIES
      if (next.length > MAX_ENTRIES) {
        const sliced = next.slice(next.length - MAX_ENTRIES);
        setCursor(sliced.length - 1);
        return sliced;
      }
      setCursor(next.length - 1);
      return next;
    });
  }, [cursor]);

  const goBack = useCallback((): NavigationEntry | null => {
    if (cursor <= 0) return null;
    const newCursor = cursor - 1;
    setCursor(newCursor);
    skipNextPushRef.current = true;
    return entries[newCursor];
  }, [cursor, entries]);

  const goForward = useCallback((): NavigationEntry | null => {
    if (cursor >= entries.length - 1) return null;
    const newCursor = cursor + 1;
    setCursor(newCursor);
    skipNextPushRef.current = true;
    return entries[newCursor];
  }, [cursor, entries]);

  const goTo = useCallback((index: number): NavigationEntry | null => {
    if (index < 0 || index >= entries.length) return null;
    setCursor(index);
    skipNextPushRef.current = true;
    return entries[index];
  }, [entries]);

  const clear = useCallback(() => {
    setEntries([]);
    setCursor(-1);
  }, []);

  const skipNextPush = useCallback(() => {
    skipNextPushRef.current = true;
  }, []);

  return {
    entries,
    cursor,
    canGoBack: cursor > 0,
    canGoForward: cursor < entries.length - 1,
    push,
    goBack,
    goForward,
    goTo,
    clear,
    skipNextPush,
  };
}
