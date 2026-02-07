import { memo, useRef, useEffect, useCallback, useMemo, useState, forwardRef, useImperativeHandle } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import fcose from "cytoscape-fcose";
import type { CodeGraph, GraphNode } from "../types/graph";
import type { FilterState } from "./Sidebar";
import { useSettings } from "../contexts/SettingsContext";
import type { GraphViewSettings } from "../types/settings";
import { ANIMATION_DURATION } from "../types/settings";
import { markStart, markEnd } from "../utils/perf";
import { GraphMinimap } from "./GraphMinimap";

// Register fCOSE extension
cytoscape.use(fcose);

type Core = cytoscape.Core;
type EventObject = cytoscape.EventObject;
type LayoutOptions = cytoscape.LayoutOptions;

// Using a looser type since data() mappers in stylesheets are valid but not well-typed
interface StylesheetDef {
  selector: string;
  style: Record<string, unknown>;
}

interface GraphViewProps {
  graph: CodeGraph;
  filters: FilterState;
  selectedNodeId: string | null;
  onNodeSelect: (nodeId: string | null) => void;
  onNodeDoubleClick: (node: GraphNode) => void;
}

export interface GraphViewHandle {
  fitGraph: () => void;
  getConnectedNodeIds: (nodeId: string) => { incoming: string[]; outgoing: string[] };
  centerOnNode: (nodeId: string) => void;
}

export type LayoutName = "fcose" | "cose" | "circle" | "grid";

const NODE_COLORS: Record<string, string> = {
  class: "#3b82f6", // blue-500
  interface: "#a855f7", // purple-500
  endpoint: "#22c55e", // green-500
  package: "#6b7280", // gray-500
  file: "#f97316", // orange-500
};

const NODE_SHAPES: Record<string, string> = {
  class: "rectangle",
  interface: "diamond",
  endpoint: "hexagon",
  package: "ellipse",
  file: "rectangle",
};

const DEFAULT_EDGE_STYLE = { lineStyle: "solid", color: "#6b7280", width: 1 };

const EDGE_STYLES: Record<string, { lineStyle: string; color: string; width: number }> = {
  extends: { lineStyle: "solid", color: "#3b82f6", width: 2 },
  implements: { lineStyle: "dashed", color: "#a855f7", width: 2 },
  imports: { lineStyle: "solid", color: "#6b7280", width: 1 },
  calls: { lineStyle: "solid", color: "#f59e0b", width: 1 },
  contains: { lineStyle: "dotted", color: "#4b5563", width: 1 },
};

const stylesheet: StylesheetDef[] = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "text-valign": "center",
      "text-halign": "center",
      "font-size": "10px",
      color: "#e5e7eb",
      "text-outline-color": "#1f2937",
      "text-outline-width": 2,
      "background-color": "data(color)",
      shape: "data(shape)",
      width: "data(size)",
      height: "data(size)",
      "border-width": 0,
    },
  },
  {
    selector: "node:selected",
    style: {
      "border-width": 3,
      "border-color": "#fbbf24",
    },
  },
  {
    selector: "node.highlighted",
    style: {
      "border-width": 3,
      "border-color": "#fbbf24",
      "background-opacity": 1,
    },
  },
  {
    selector: "node.faded",
    style: {
      opacity: 0.3,
    },
  },
  {
    selector: "edge",
    style: {
      width: "data(width)",
      "line-color": "data(color)",
      "line-style": "data(lineStyle)",
      "target-arrow-color": "data(color)",
      "target-arrow-shape": "triangle",
      "curve-style": "bezier",
      opacity: 0.7,
    },
  },
  {
    selector: "edge.faded",
    style: {
      opacity: 0.1,
    },
  },
  {
    selector: "edge.highlighted",
    style: {
      opacity: 1,
      width: 3,
    },
  },
  {
    selector: ":parent",
    style: {
      "background-color": "#1e293b",
      "background-opacity": 0.3,
      "border-color": "#475569",
      "border-width": 1,
      "shape": "roundrectangle",
      padding: "20px",
      "text-valign": "top",
      "text-halign": "center",
      "font-size": "11px",
      color: "#94a3b8",
      "text-outline-width": 0,
    },
  },
  {
    selector: "node[?collapsed]",
    style: {
      "border-width": 2,
      "border-color": "#6b7280",
      "border-style": "dashed",
      "shape": "roundrectangle",
    },
  },
];

interface TooltipState {
  x: number;
  y: number;
  label: string;
  nodeType: string;
  methodCount?: number;
  fieldCount?: number;
  method?: string;
  handler?: string;
}

export const GraphView = memo(forwardRef<GraphViewHandle, GraphViewProps>(function GraphView({
  graph,
  filters,
  selectedNodeId,
  onNodeSelect,
  onNodeDoubleClick,
}, ref) {
  const cyRef = useRef<Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { settings } = useSettings();
  const graphSettings = settings.graphView;

  // Tooltip state
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const tooltipTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Export menu state
  const [showExportMenu, setShowExportMenu] = useState(false);
  const exportMenuRef = useRef<HTMLDivElement>(null);

  // Minimap state
  const [cyInstance, setCyInstance] = useState<Core | null>(null);
  const [showMinimap, setShowMinimap] = useState(true);

  // Package clustering state
  const [clusteringEnabled, setClusteringEnabled] = useState(true);
  const [collapsedPackages, setCollapsedPackages] = useState<Set<string>>(() => new Set());
  const clusteringEnabledRef = useRef(clusteringEnabled);
  clusteringEnabledRef.current = clusteringEnabled;

  // Close export menu on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (exportMenuRef.current && !exportMenuRef.current.contains(e.target as Node)) {
        setShowExportMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Imperative handle for keyboard navigation
  useImperativeHandle(ref, () => ({
    fitGraph() {
      const cy = cyRef.current;
      if (cy) cy.fit(undefined, 50);
    },
    getConnectedNodeIds(nodeId: string) {
      const cy = cyRef.current;
      if (!cy) return { incoming: [], outgoing: [] };
      const node = cy.getElementById(nodeId);
      if (!node.length) return { incoming: [], outgoing: [] };
      const incoming = node.incomers("node").map((n) => n.id());
      const outgoing = node.outgoers("node").map((n) => n.id());
      return { incoming, outgoing };
    },
    centerOnNode(nodeId: string) {
      const cy = cyRef.current;
      if (!cy) return;
      const node = cy.getElementById(nodeId);
      if (node.length) {
        cy.animate({ center: { eles: node }, duration: 200 });
      }
    },
  }), []);

  // Initialize collapsed packages when graph changes
  useEffect(() => {
    if (clusteringEnabled) {
      const pkgIds = new Set(
        graph.nodes.filter((n) => n.type === "package").map((n) => n.id)
      );
      setCollapsedPackages(pkgIds);
    } else {
      setCollapsedPackages(new Set());
    }
  }, [graph, clusteringEnabled]);

  // Calculate node degrees (connection count) for sizing
  const nodeDegrees = useMemo(() => {
    const degrees = new Map<string, number>();
    graph.nodes.forEach((node) => degrees.set(node.id, 0));
    graph.edges.forEach((edge) => {
      degrees.set(edge.source, (degrees.get(edge.source) || 0) + 1);
      degrees.set(edge.target, (degrees.get(edge.target) || 0) + 1);
    });
    return degrees;
  }, [graph]);

  // Convert graph data to Cytoscape elements
  const elements = useMemo(() => {
    markStart("graph:buildElements");

    // Filter nodes
    const filteredNodes = graph.nodes.filter((node) => {
      if (!filters.nodeTypes.has(node.type)) return false;
      const category = node.metadata.category || "unknown";
      if (!filters.categories.has(category)) return false;
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesLabel = node.label.toLowerCase().includes(query);
        const matchesFqn = node.metadata.fqn?.toLowerCase().includes(query) ?? false;
        if (!matchesLabel && !matchesFqn) return false;
      }
      return true;
    });

    const nodeElements: { data: Record<string, unknown> }[] = [];
    const visibleNodeIds = new Set<string>();
    let collapsedChildToPackage: Map<string, string> | null = null;

    if (clusteringEnabled) {
      // Build package map: package name -> package node id
      const packageNameToId = new Map<string, string>();
      const packageChildCounts = new Map<string, number>();

      for (const node of filteredNodes) {
        if (node.type === "package") {
          const pkgName = node.id.replace(/^pkg:/, "");
          packageNameToId.set(pkgName, node.id);
          packageChildCounts.set(node.id, 0);
        }
      }

      // Count children per package
      for (const node of filteredNodes) {
        if (node.type !== "package" && node.metadata.package) {
          const pkgId = packageNameToId.get(node.metadata.package);
          if (pkgId) {
            packageChildCounts.set(pkgId, (packageChildCounts.get(pkgId) || 0) + 1);
          }
        }
      }

      // Build collapsed child map for edge rerouting
      collapsedChildToPackage = new Map();
      for (const node of filteredNodes) {
        if (node.type !== "package" && node.metadata.package) {
          const pkgId = packageNameToId.get(node.metadata.package);
          if (pkgId && collapsedPackages.has(pkgId)) {
            collapsedChildToPackage.set(node.id, pkgId);
          }
        }
      }

      for (const node of filteredNodes) {
        if (node.type === "package") {
          const isCollapsed = collapsedPackages.has(node.id);
          const childCount = packageChildCounts.get(node.id) || 0;
          const label = isCollapsed && childCount > 0
            ? `${node.label} (${childCount})`
            : node.label;

          visibleNodeIds.add(node.id);
          nodeElements.push({
            data: {
              id: node.id,
              label,
              color: NODE_COLORS.package,
              shape: "roundrectangle",
              size: isCollapsed
                ? Math.max(40, 30 + childCount * 3)
                : getNodeSize(node, graphSettings.nodeSizing, nodeDegrees.get(node.id) || 0),
              nodeType: "package",
              collapsed: isCollapsed,
              ...node.metadata,
            },
          });
        } else {
          const pkgId = node.metadata.package
            ? packageNameToId.get(node.metadata.package)
            : undefined;

          // Skip children inside collapsed packages
          if (pkgId && collapsedPackages.has(pkgId)) continue;

          visibleNodeIds.add(node.id);
          nodeElements.push({
            data: {
              id: node.id,
              label: node.label,
              color: NODE_COLORS[node.type] || "#6b7280",
              shape: NODE_SHAPES[node.type] || "ellipse",
              size: getNodeSize(node, graphSettings.nodeSizing, nodeDegrees.get(node.id) || 0),
              nodeType: node.type,
              ...node.metadata,
              ...(pkgId ? { parent: pkgId } : {}),
            },
          });
        }
      }
    } else {
      // Non-clustered mode (original behavior)
      for (const node of filteredNodes) {
        visibleNodeIds.add(node.id);
        nodeElements.push({
          data: {
            id: node.id,
            label: node.label,
            color: NODE_COLORS[node.type] || "#6b7280",
            shape: NODE_SHAPES[node.type] || "ellipse",
            size: getNodeSize(node, graphSettings.nodeSizing, nodeDegrees.get(node.id) || 0),
            nodeType: node.type,
            ...node.metadata,
          },
        });
      }
    }

    // Build edges with rerouting for collapsed packages
    const edgeSet = new Set<string>();
    const edgeElements: { data: Record<string, unknown> }[] = [];

    for (const edge of graph.edges) {
      // Skip "contains" edges when clustering (containment is structural)
      if (clusteringEnabled && edge.type === "contains") continue;

      let source = edge.source;
      let target = edge.target;

      // Reroute edges for collapsed packages
      if (collapsedChildToPackage) {
        const rSource = collapsedChildToPackage.get(source);
        const rTarget = collapsedChildToPackage.get(target);
        if (rSource) source = rSource;
        if (rTarget) target = rTarget;
      }

      // Skip self-edges and edges to non-visible nodes
      if (source === target) continue;
      if (!visibleNodeIds.has(source) || !visibleNodeIds.has(target)) continue;

      // Deduplicate rerouted edges
      const edgeKey = `${source}-${edge.type}-${target}`;
      if (edgeSet.has(edgeKey)) continue;
      edgeSet.add(edgeKey);

      const style = EDGE_STYLES[edge.type] || DEFAULT_EDGE_STYLE;
      edgeElements.push({
        data: {
          id: edgeKey,
          source,
          target,
          edgeType: edge.type,
          ...style,
        },
      });
    }

    const result = [...nodeElements, ...edgeElements];
    markEnd("graph:buildElements");
    return result;
  }, [graph, filters, graphSettings.nodeSizing, nodeDegrees, clusteringEnabled, collapsedPackages]);

  // Handle node selection highlighting
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    // Reset all nodes and edges
    cy.elements().removeClass("highlighted faded");

    if (selectedNodeId) {
      const selectedNode = cy.getElementById(selectedNodeId);
      if (selectedNode.length) {
        // Highlight selected node and connected edges/nodes
        selectedNode.addClass("highlighted");
        const connectedEdges = selectedNode.connectedEdges();
        const connectedNodes = connectedEdges.connectedNodes();

        connectedEdges.addClass("highlighted");
        connectedNodes.addClass("highlighted");

        // Fade unconnected elements
        cy.elements()
          .not(selectedNode)
          .not(connectedEdges)
          .not(connectedNodes)
          .addClass("faded");
      }
    }
  }, [selectedNodeId]);

  // Run layout when graph data or layout settings change (not on collapse/expand)
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || graph.nodes.length === 0) return;

    // Run layout with animation settings
    const animationDuration = ANIMATION_DURATION[graphSettings.animationSpeed];
    const layoutName = graphSettings.defaultLayout;
    const nodeCount = graph.nodes.length;
    markStart("graph:layout");
    const layout = cy.layout(
      getLayoutOptions(layoutName, {
        nodeCount,
        animationDuration,
        quality: graphSettings.layoutQuality,
        largeGraphThreshold: graphSettings.largeGraphThreshold,
      })
    );
    layout.on("layoutstop", () => markEnd("graph:layout"));
    layout.run();
  }, [graph, graphSettings.animationSpeed, graphSettings.defaultLayout, graphSettings.layoutQuality, graphSettings.largeGraphThreshold]);

  const handleCyInit = useCallback((cy: Core) => {
    cyRef.current = cy;
    setCyInstance(cy);

    // Node click handler
    cy.on("tap", "node", (event: EventObject) => {
      const nodeId = event.target.id();
      const nodeType = event.target.data("nodeType");

      // Toggle package collapse when clustering is enabled
      if (clusteringEnabledRef.current && nodeType === "package") {
        setCollapsedPackages((prev) => {
          const next = new Set(prev);
          if (next.has(nodeId)) {
            next.delete(nodeId);
          } else {
            next.add(nodeId);
          }
          return next;
        });
      }

      onNodeSelect(nodeId);
    });

    // Node double-click handler
    cy.on("dbltap", "node", (event: EventObject) => {
      const nodeData = event.target.data();
      const node: GraphNode = {
        id: nodeData.id,
        label: nodeData.label,
        type: nodeData.nodeType,
        metadata: {
          fqn: nodeData.fqn,
          path: nodeData.path,
          relativePath: nodeData.relativePath,
          line: nodeData.line,
          category: nodeData.category,
        },
      };
      onNodeDoubleClick(node);
    });

    // Background click handler
    cy.on("tap", (event: EventObject) => {
      if (event.target === cy) {
        onNodeSelect(null);
      }
    });

    // Tooltip: mouseover node
    cy.on("mouseover", "node", (event: EventObject) => {
      if (tooltipTimeoutRef.current) clearTimeout(tooltipTimeoutRef.current);
      const target = event.target;
      tooltipTimeoutRef.current = setTimeout(() => {
        const renderedPos = target.renderedPosition();
        const data = target.data();
        setTooltip({
          x: renderedPos.x,
          y: renderedPos.y - (target.renderedHeight() / 2) - 8,
          label: data.label,
          nodeType: data.nodeType,
          methodCount: data.methodCount,
          fieldCount: data.fieldCount,
          method: data.method,
          handler: data.handler,
        });
      }, 300);
    });

    // Tooltip: mouseout node
    cy.on("mouseout", "node", () => {
      if (tooltipTimeoutRef.current) {
        clearTimeout(tooltipTimeoutRef.current);
        tooltipTimeoutRef.current = null;
      }
      setTooltip(null);
    });

    // Tooltip: hide on viewport change or tap
    cy.on("viewport tap", () => {
      setTooltip(null);
      if (tooltipTimeoutRef.current) {
        clearTimeout(tooltipTimeoutRef.current);
        tooltipTimeoutRef.current = null;
      }
    });
  }, [onNodeSelect, onNodeDoubleClick]);

  // Cleanup tooltip timeout on unmount
  useEffect(() => {
    return () => {
      if (tooltipTimeoutRef.current) clearTimeout(tooltipTimeoutRef.current);
    };
  }, []);

  const handleLayout = useCallback((layoutName: LayoutName) => {
    const cy = cyRef.current;
    if (!cy) return;

    const animationDuration = ANIMATION_DURATION[graphSettings.animationSpeed];
    const nodeCount = graph.nodes.length;
    markStart("graph:layout");
    const layout = cy.layout(
      getLayoutOptions(layoutName, {
        nodeCount,
        animationDuration,
        quality: graphSettings.layoutQuality,
        largeGraphThreshold: graphSettings.largeGraphThreshold,
      })
    );
    layout.on("layoutstop", () => markEnd("graph:layout"));
    layout.run();
  }, [graph.nodes.length, graphSettings.animationSpeed, graphSettings.layoutQuality, graphSettings.largeGraphThreshold]);

  const handleFitGraph = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.fit(undefined, 50);
  }, []);

  const handleZoomIn = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom(cy.zoom() * 1.2);
  }, []);

  const handleZoomOut = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom(cy.zoom() / 1.2);
  }, []);

  const handleExportPNG = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const dataUri = cy.png({ bg: "#111827", full: true, scale: 2 });
    const link = document.createElement("a");
    link.href = dataUri;
    link.download = "graph.png";
    link.click();
    setShowExportMenu(false);
  }, []);

  const handleExportSVG = useCallback(() => {
    const cy = cyRef.current;
    if (!cy) return;
    const svgStr = (cy as unknown as { svg(opts: Record<string, unknown>): string }).svg({ full: true, bg: "#111827" });
    const blob = new Blob([svgStr], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "graph.svg";
    link.click();
    URL.revokeObjectURL(url);
    setShowExportMenu(false);
  }, []);

  // Build tooltip metrics string
  const tooltipMetrics = useMemo(() => {
    if (!tooltip) return null;
    const parts: string[] = [];
    if (tooltip.nodeType === "class" || tooltip.nodeType === "interface") {
      if (tooltip.methodCount !== undefined) parts.push(`${tooltip.methodCount} methods`);
      if (tooltip.fieldCount !== undefined) parts.push(`${tooltip.fieldCount} fields`);
    }
    if (tooltip.nodeType === "endpoint") {
      if (tooltip.method) parts.push(tooltip.method);
      if (tooltip.handler) parts.push(tooltip.handler);
    }
    return parts.length > 0 ? parts.join(" \u00b7 ") : null;
  }, [tooltip]);

  return (
    <div ref={containerRef} className="flex-1 relative bg-gray-900">
      {/* Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <div className="bg-gray-800 rounded-lg shadow-lg flex">
          <button
            onClick={() => handleLayout("fcose")}
            className="px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-l-lg"
            title="Force-directed layout (fCoSE)"
          >
            Force
          </button>
          <button
            onClick={() => handleLayout("circle")}
            className="px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 border-l border-gray-700"
            title="Circular layout"
          >
            Circle
          </button>
          <button
            onClick={() => handleLayout("grid")}
            className="px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-r-lg border-l border-gray-700"
            title="Grid layout"
          >
            Grid
          </button>
        </div>

        <div className="bg-gray-800 rounded-lg shadow-lg flex">
          <button
            onClick={handleZoomIn}
            className="px-3 py-2 text-gray-300 hover:bg-gray-700 rounded-l-lg"
            title="Zoom in"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
          </button>
          <button
            onClick={handleZoomOut}
            className="px-3 py-2 text-gray-300 hover:bg-gray-700 border-l border-gray-700"
            title="Zoom out"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20 12H4" />
            </svg>
          </button>
          <button
            onClick={handleFitGraph}
            className="px-3 py-2 text-gray-300 hover:bg-gray-700 rounded-r-lg border-l border-gray-700"
            title="Fit to screen (f)"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        </div>

        {/* Export button */}
        <div className="relative" ref={exportMenuRef}>
          <button
            onClick={() => setShowExportMenu(!showExportMenu)}
            className="bg-gray-800 rounded-lg shadow-lg px-3 py-2 text-gray-300 hover:bg-gray-700 flex items-center gap-1.5"
            title="Export graph"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            <span className="text-sm">Export</span>
          </button>
          {showExportMenu && (
            <div className="absolute top-full left-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50 min-w-[120px]">
              <button
                onClick={handleExportPNG}
                className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 rounded-t-lg"
              >
                PNG
              </button>
              <button
                onClick={handleExportSVG}
                className="w-full px-3 py-2 text-left text-sm text-gray-300 hover:bg-gray-700 rounded-b-lg border-t border-gray-700"
              >
                SVG
              </button>
            </div>
          )}
        </div>

        {/* Minimap toggle */}
        <button
          onClick={() => setShowMinimap(!showMinimap)}
          className={`bg-gray-800 rounded-lg shadow-lg px-3 py-2 text-sm hover:bg-gray-700 ${showMinimap ? "text-blue-400" : "text-gray-300"}`}
          title="Toggle minimap"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
        </button>

        {/* Package clustering toggle */}
        <button
          onClick={() => setClusteringEnabled(!clusteringEnabled)}
          className={`bg-gray-800 rounded-lg shadow-lg px-3 py-2 text-sm hover:bg-gray-700 ${clusteringEnabled ? "text-blue-400" : "text-gray-300"}`}
          title="Toggle package clustering"
        >
          Cluster
        </button>

        {/* Expand/Collapse all packages */}
        {clusteringEnabled && (
          <div className="bg-gray-800 rounded-lg shadow-lg flex">
            <button
              onClick={() => {
                const pkgIds = new Set(
                  graph.nodes.filter((n) => n.type === "package").map((n) => n.id)
                );
                setCollapsedPackages(pkgIds);
              }}
              className="px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-l-lg"
              title="Collapse all packages"
            >
              Collapse All
            </button>
            <button
              onClick={() => setCollapsedPackages(new Set())}
              className="px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-r-lg border-l border-gray-700"
              title="Expand all packages"
            >
              Expand All
            </button>
          </div>
        )}
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-gray-800 rounded-lg shadow-lg p-3">
        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Legend</h4>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded-sm" style={{ backgroundColor: color }} />
              <span className="text-gray-300 capitalize">{type}</span>
            </div>
          ))}
        </div>
        <div className="mt-2 pt-2 border-t border-gray-700 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-blue-500" />
            <span className="text-gray-400">extends</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-purple-500 border-dashed" style={{ borderTopWidth: 2, borderStyle: "dashed" }} />
            <span className="text-gray-400">implements</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-gray-500" />
            <span className="text-gray-400">imports</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-4 h-0.5 bg-gray-600" style={{ borderTopWidth: 2, borderStyle: "dotted" }} />
            <span className="text-gray-400">contains</span>
          </div>
        </div>
      </div>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="absolute z-20 pointer-events-none bg-gray-800 border border-gray-600 rounded-lg px-3 py-2 shadow-xl text-xs max-w-[220px]"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
          }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <span
              className="w-2 h-2 rounded-full shrink-0"
              style={{ backgroundColor: NODE_COLORS[tooltip.nodeType] || "#6b7280" }}
            />
            <span className="text-gray-400 capitalize">{tooltip.nodeType}</span>
          </div>
          <div className="text-gray-100 font-medium truncate">{tooltip.label}</div>
          {tooltipMetrics && (
            <div className="text-gray-400 mt-0.5">{tooltipMetrics}</div>
          )}
        </div>
      )}

      {/* Minimap */}
      {showMinimap && <GraphMinimap cy={cyInstance} />}

      {/* Graph */}
      {elements.length > 0 ? (
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          cy={handleCyInit}
          style={{ width: "100%", height: "100%" }}
          wheelSensitivity={graphSettings.scrollSpeed}
          minZoom={0.1}
          maxZoom={3}
        />
      ) : (
        <div className="flex items-center justify-center h-full text-gray-500">
          <div className="text-center">
            <svg className="w-16 h-16 mx-auto mb-4 opacity-50" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <p>No nodes to display</p>
            <p className="text-sm">Adjust filters or load a project</p>
          </div>
        </div>
      )}
    </div>
  );
}));

function getNodeSize(
  node: GraphNode,
  sizingMode: GraphViewSettings["nodeSizing"],
  degree: number
): number {
  const BASE = 30;
  const MIN = 20;
  const MAX = 80;

  switch (sizingMode) {
    case "fixed":
      return BASE;
    case "byType":
      // Original type-based sizing
      switch (node.type) {
        case "package":
          return 50;
        case "class":
        case "interface": {
          const methodCount = node.metadata.methodCount || 0;
          return Math.min(60, Math.max(30, 30 + methodCount * 2));
        }
        case "endpoint":
          return 25;
        case "file":
          return 20;
        default:
          return 30;
      }
    case "byDegree":
      // Logarithmic scale based on connections
      return Math.min(MAX, Math.max(MIN, BASE + Math.log2(degree + 1) * 8));
    default:
      return BASE;
  }
}

interface LayoutConfig {
  nodeCount: number;
  animationDuration: number;
  quality: GraphViewSettings["layoutQuality"];
  largeGraphThreshold: number;
}

function getLayoutOptions(name: LayoutName, config: LayoutConfig): LayoutOptions {
  const isLarge = config.nodeCount > config.largeGraphThreshold;
  const shouldAnimate = config.animationDuration > 0 && !isLarge;

  const baseOptions = {
    name,
    animate: shouldAnimate,
    animationDuration: shouldAnimate ? config.animationDuration : 0,
  };

  switch (name) {
    case "fcose":
      return {
        ...baseOptions,
        name: "fcose",
        quality: config.quality,
        fit: true,
        padding: 30,
        nodeSeparation: 100,
        nodeRepulsion: () => 4500,
        idealEdgeLength: () => 80,
        edgeElasticity: () => 0.45,
        gravity: 0.25,
        numIter: isLarge ? 500 : 2500,
        randomize: true,
        tile: true,
      } as LayoutOptions;
    case "cose":
      return {
        ...baseOptions,
        name: "cose",
        idealEdgeLength: 100,
        nodeOverlap: 20,
        refresh: 20,
        fit: true,
        padding: 30,
        randomize: false,
        componentSpacing: 100,
        nodeRepulsion: 400000,
        edgeElasticity: 100,
        nestingFactor: 5,
        gravity: 80,
        numIter: isLarge ? 200 : 500,
        initialTemp: 200,
        coolingFactor: 0.95,
        minTemp: 1.0,
      };
    case "circle":
      return {
        ...baseOptions,
        name: "circle",
        fit: true,
        padding: 30,
        avoidOverlap: true,
        spacingFactor: 1.5,
      };
    case "grid":
      return {
        ...baseOptions,
        name: "grid",
        fit: true,
        padding: 30,
        avoidOverlap: true,
        condense: true,
      };
    default:
      return baseOptions;
  }
}
