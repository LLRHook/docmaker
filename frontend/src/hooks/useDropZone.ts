import { useState, useCallback, useEffect, useRef } from "react";
import { createLogger } from "../utils/logger";

const logger = createLogger("useDropZone");

interface UseDropZoneOptions {
  onDrop: (path: string) => void;
}

/**
 * Hook for handling drag-and-drop of folders onto the application window.
 *
 * Uses the HTML5 File System Access API (webkitGetAsEntry) to detect
 * whether the dropped item is a directory. In Pyloid (PySide6 webview),
 * dropped files carry an absolute path property.
 */
export function useDropZone({ onDrop }: UseDropZoneOptions) {
  const [isDragging, setIsDragging] = useState(false);
  const dragCounterRef = useRef(0);

  const handleDragEnter = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (dragCounterRef.current === 1) {
      setIsDragging(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragging(false);
    }
  }, []);

  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback((e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = 0;
    setIsDragging(false);

    const dt = e.dataTransfer;
    if (!dt) return;

    // Try webkitGetAsEntry first — works in modern browsers and Pyloid webview
    const items = dt.items;
    if (items && items.length > 0) {
      const entry = items[0].webkitGetAsEntry?.();
      if (entry?.isDirectory) {
        // In Pyloid/QtWebEngine, files carry a .path with the absolute filesystem path
        const file = dt.files[0];
        const path = (file as File & { path?: string }).path;
        if (path) {
          logger.info("Dropped directory (Pyloid path):", path);
          onDrop(path);
          return;
        }
        // Fallback: entry.fullPath gives us a virtual path like "/dirname"
        // which is useful as a display name but not a filesystem path
        logger.info("Dropped directory entry:", entry.fullPath);
        onDrop(entry.fullPath);
        return;
      }
    }

    // Fallback: check files directly (Pyloid provides .path on File objects)
    if (dt.files.length > 0) {
      const file = dt.files[0];
      const path = (file as File & { path?: string }).path;
      if (path) {
        logger.info("Dropped file/folder (Pyloid path):", path);
        onDrop(path);
        return;
      }
    }

    logger.warn("Drop event did not contain a usable folder path");
  }, [onDrop]);

  useEffect(() => {
    document.addEventListener("dragenter", handleDragEnter);
    document.addEventListener("dragleave", handleDragLeave);
    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("drop", handleDrop);

    return () => {
      document.removeEventListener("dragenter", handleDragEnter);
      document.removeEventListener("dragleave", handleDragLeave);
      document.removeEventListener("dragover", handleDragOver);
      document.removeEventListener("drop", handleDrop);
    };
  }, [handleDragEnter, handleDragLeave, handleDragOver, handleDrop]);

  return { isDragging };
}
