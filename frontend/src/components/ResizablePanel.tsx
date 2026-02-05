import { useState, useCallback, useEffect, useRef } from "react";

interface ResizablePanelProps {
  children: React.ReactNode;
  width: number;
  minWidth: number;
  maxWidth: number;
  onWidthChange: (width: number) => void;
  side: "left" | "right";
  className?: string;
}

export function ResizablePanel({
  children,
  width,
  minWidth,
  maxWidth,
  onWidthChange,
  side,
  className = "",
}: ResizablePanelProps) {
  const [isDragging, setIsDragging] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const startXRef = useRef(0);
  const startWidthRef = useRef(0);

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setIsDragging(true);
      startXRef.current = e.clientX;
      startWidthRef.current = width;
    },
    [width]
  );

  useEffect(() => {
    if (!isDragging) return;

    const handleMouseMove = (e: MouseEvent) => {
      const delta = side === "left"
        ? e.clientX - startXRef.current
        : startXRef.current - e.clientX;
      const newWidth = Math.min(maxWidth, Math.max(minWidth, startWidthRef.current + delta));
      onWidthChange(newWidth);
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    return () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDragging, minWidth, maxWidth, onWidthChange, side]);

  const handleStyle = side === "left"
    ? { right: 0, cursor: "ew-resize" }
    : { left: 0, cursor: "ew-resize" };

  return (
    <div
      ref={panelRef}
      className={`relative flex-shrink-0 ${className}`}
      style={{ width }}
    >
      {children}

      {/* Resize handle */}
      <div
        className={`absolute top-0 bottom-0 w-1 hover:bg-blue-500/50 transition-colors z-20 ${
          isDragging ? "bg-blue-500" : "bg-transparent"
        }`}
        style={handleStyle}
        onMouseDown={handleMouseDown}
      />

      {/* Wider invisible hit area for easier grabbing */}
      <div
        className="absolute top-0 bottom-0 w-2 cursor-ew-resize z-10"
        style={side === "left" ? { right: -2 } : { left: -2 }}
        onMouseDown={handleMouseDown}
      />
    </div>
  );
}
