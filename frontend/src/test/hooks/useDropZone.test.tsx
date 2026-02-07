import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useDropZone } from "../../hooks/useDropZone";

describe("useDropZone", () => {
  let onDrop: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onDrop = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("starts with isDragging false", () => {
    const { result } = renderHook(() => useDropZone({ onDrop }));
    expect(result.current.isDragging).toBe(false);
  });

  it("sets isDragging true on dragenter", () => {
    const { result } = renderHook(() => useDropZone({ onDrop }));

    act(() => {
      document.dispatchEvent(new Event("dragenter"));
    });

    expect(result.current.isDragging).toBe(true);
  });

  it("sets isDragging false after all dragleave events balance", () => {
    const { result } = renderHook(() => useDropZone({ onDrop }));

    act(() => {
      document.dispatchEvent(new Event("dragenter"));
      document.dispatchEvent(new Event("dragenter"));
    });
    expect(result.current.isDragging).toBe(true);

    act(() => {
      document.dispatchEvent(new Event("dragleave"));
    });
    // Still dragging — one nested element left
    expect(result.current.isDragging).toBe(true);

    act(() => {
      document.dispatchEvent(new Event("dragleave"));
    });
    expect(result.current.isDragging).toBe(false);
  });

  it("resets isDragging on drop", () => {
    const { result } = renderHook(() => useDropZone({ onDrop }));

    act(() => {
      document.dispatchEvent(new Event("dragenter"));
    });
    expect(result.current.isDragging).toBe(true);

    act(() => {
      const dropEvent = new Event("drop") as Event & { dataTransfer?: unknown };
      // Minimal dataTransfer mock
      Object.defineProperty(dropEvent, "dataTransfer", {
        value: { items: [], files: [] },
      });
      document.dispatchEvent(dropEvent);
    });

    expect(result.current.isDragging).toBe(false);
  });

  it("calls onDrop with path from Pyloid File.path", () => {
    const { result } = renderHook(() => useDropZone({ onDrop }));

    act(() => {
      document.dispatchEvent(new Event("dragenter"));
    });

    act(() => {
      const file = new File([""], "project", { type: "" });
      Object.defineProperty(file, "path", { value: "/home/user/my-project" });

      const dropEvent = new Event("drop") as Event & { dataTransfer?: unknown };
      Object.defineProperty(dropEvent, "dataTransfer", {
        value: {
          items: [
            {
              webkitGetAsEntry: () => ({ isDirectory: true, fullPath: "/project" }),
            },
          ],
          files: [file],
        },
      });
      document.dispatchEvent(dropEvent);
    });

    expect(result.current.isDragging).toBe(false);
    expect(onDrop).toHaveBeenCalledWith("/home/user/my-project");
  });

  it("falls back to entry.fullPath when File.path not available", () => {
    const { result } = renderHook(() => useDropZone({ onDrop }));

    act(() => {
      const file = new File([""], "project", { type: "" });
      // No .path property (browser context without Pyloid)

      const dropEvent = new Event("drop") as Event & { dataTransfer?: unknown };
      Object.defineProperty(dropEvent, "dataTransfer", {
        value: {
          items: [
            {
              webkitGetAsEntry: () => ({ isDirectory: true, fullPath: "/project" }),
            },
          ],
          files: [file],
        },
      });
      document.dispatchEvent(dropEvent);
    });

    expect(onDrop).toHaveBeenCalledWith("/project");
  });

  it("falls back to File.path when no webkitGetAsEntry", () => {
    renderHook(() => useDropZone({ onDrop }));

    act(() => {
      const file = new File([""], "project", { type: "" });
      Object.defineProperty(file, "path", { value: "/home/user/project" });

      const dropEvent = new Event("drop") as Event & { dataTransfer?: unknown };
      Object.defineProperty(dropEvent, "dataTransfer", {
        value: {
          items: [{ webkitGetAsEntry: undefined }],
          files: [file],
        },
      });
      document.dispatchEvent(dropEvent);
    });

    expect(onDrop).toHaveBeenCalledWith("/home/user/project");
  });

  it("cleans up event listeners on unmount", () => {
    const addSpy = vi.spyOn(document, "addEventListener");
    const removeSpy = vi.spyOn(document, "removeEventListener");

    const { unmount } = renderHook(() => useDropZone({ onDrop }));

    const addedEvents = addSpy.mock.calls.map((c) => c[0]);
    expect(addedEvents).toContain("dragenter");
    expect(addedEvents).toContain("dragleave");
    expect(addedEvents).toContain("dragover");
    expect(addedEvents).toContain("drop");

    unmount();

    const removedEvents = removeSpy.mock.calls.map((c) => c[0]);
    expect(removedEvents).toContain("dragenter");
    expect(removedEvents).toContain("dragleave");
    expect(removedEvents).toContain("dragover");
    expect(removedEvents).toContain("drop");
  });
});
