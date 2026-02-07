import { memo, useRef, useEffect, useCallback } from "react";
import type cytoscape from "cytoscape";

const WIDTH = 160;
const HEIGHT = 120;

const NODE_COLORS: Record<string, string> = {
  class: "#3b82f6",
  interface: "#a855f7",
  endpoint: "#22c55e",
  package: "#6b7280",
  file: "#f97316",
};

interface GraphMinimapProps {
  cy: cytoscape.Core | null;
}

export const GraphMinimap = memo(function GraphMinimap({ cy }: GraphMinimapProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);
  const isDraggingRef = useRef(false);

  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas || !cy) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    ctx.clearRect(0, 0, WIDTH, HEIGHT);

    // Background
    ctx.fillStyle = "#1f2937";
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    const bb = cy.elements().boundingBox();
    if (bb.w === 0 || bb.h === 0) return;

    const padding = 10;
    const scaleX = (WIDTH - padding * 2) / bb.w;
    const scaleY = (HEIGHT - padding * 2) / bb.h;
    const scale = Math.min(scaleX, scaleY);

    const offsetX = padding + (WIDTH - padding * 2 - bb.w * scale) / 2;
    const offsetY = padding + (HEIGHT - padding * 2 - bb.h * scale) / 2;

    const toMinimapX = (x: number) => offsetX + (x - bb.x1) * scale;
    const toMinimapY = (y: number) => offsetY + (y - bb.y1) * scale;

    // Draw nodes
    cy.nodes().forEach((node) => {
      const pos = node.position();
      const mx = toMinimapX(pos.x);
      const my = toMinimapY(pos.y);
      const nodeType = node.data("nodeType") as string;
      const isFaded = node.hasClass("faded");

      ctx.globalAlpha = isFaded ? 0.15 : 0.8;
      ctx.fillStyle = NODE_COLORS[nodeType] || "#6b7280";
      ctx.beginPath();
      ctx.arc(mx, my, 2.5, 0, Math.PI * 2);
      ctx.fill();
    });

    ctx.globalAlpha = 1;

    // Draw viewport rectangle
    const ext = cy.extent();
    const vx1 = toMinimapX(ext.x1);
    const vy1 = toMinimapY(ext.y1);
    const vx2 = toMinimapX(ext.x2);
    const vy2 = toMinimapY(ext.y2);

    ctx.strokeStyle = "#fbbf24";
    ctx.lineWidth = 1.5;
    ctx.strokeRect(vx1, vy1, vx2 - vx1, vy2 - vy1);
  }, [cy]);

  const scheduleRedraw = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    rafRef.current = requestAnimationFrame(draw);
  }, [draw]);

  useEffect(() => {
    if (!cy) return;

    const events = "viewport position add remove";
    cy.on(events, scheduleRedraw);
    scheduleRedraw();

    return () => {
      cy.off(events, scheduleRedraw);
      cancelAnimationFrame(rafRef.current);
    };
  }, [cy, scheduleRedraw]);

  const panToMinimapPosition = useCallback(
    (clientX: number, clientY: number) => {
      if (!cy) return;
      const canvas = canvasRef.current;
      if (!canvas) return;

      const rect = canvas.getBoundingClientRect();
      const mx = clientX - rect.left;
      const my = clientY - rect.top;

      const bb = cy.elements().boundingBox();
      if (bb.w === 0 || bb.h === 0) return;

      const padding = 10;
      const scaleX = (WIDTH - padding * 2) / bb.w;
      const scaleY = (HEIGHT - padding * 2) / bb.h;
      const scale = Math.min(scaleX, scaleY);

      const offsetX = padding + (WIDTH - padding * 2 - bb.w * scale) / 2;
      const offsetY = padding + (HEIGHT - padding * 2 - bb.h * scale) / 2;

      const graphX = bb.x1 + (mx - offsetX) / scale;
      const graphY = bb.y1 + (my - offsetY) / scale;

      cy.center({ eles: cy.collection(), x: graphX, y: graphY } as unknown as cytoscape.CollectionArgument);
      // Pan to the computed position
      const currentCenter = {
        x: (cy.extent().x1 + cy.extent().x2) / 2,
        y: (cy.extent().y1 + cy.extent().y2) / 2,
      };
      cy.panBy({
        x: (currentCenter.x - graphX) * cy.zoom(),
        y: (currentCenter.y - graphY) * cy.zoom(),
      });
    },
    [cy]
  );

  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      isDraggingRef.current = true;
      panToMinimapPosition(e.clientX, e.clientY);
    },
    [panToMinimapPosition]
  );

  const handleMouseMove = useCallback(
    (e: React.MouseEvent) => {
      if (!isDraggingRef.current) return;
      panToMinimapPosition(e.clientX, e.clientY);
    },
    [panToMinimapPosition]
  );

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false;
  }, []);

  useEffect(() => {
    const handleGlobalMouseUp = () => {
      isDraggingRef.current = false;
    };
    document.addEventListener("mouseup", handleGlobalMouseUp);
    return () => document.removeEventListener("mouseup", handleGlobalMouseUp);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      width={WIDTH}
      height={HEIGHT}
      className="absolute bottom-4 right-4 z-10 rounded-lg border border-gray-700 cursor-crosshair"
      style={{ width: WIDTH, height: HEIGHT }}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
    />
  );
});
