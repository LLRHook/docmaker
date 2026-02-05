import { useRef, useEffect, useCallback, useMemo } from "react";
import CytoscapeComponent from "react-cytoscapejs";
import cytoscape from "cytoscape";
import type { CodeGraph, GraphNode } from "../types/graph";
import type { FilterState } from "./Sidebar";

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

type LayoutName = "cose" | "dagre" | "circle" | "grid";

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

const EDGE_STYLES: Record<string, { lineStyle: string; lineColor: string; width: number }> = {
  extends: { lineStyle: "solid", lineColor: "#3b82f6", width: 2 },
  implements: { lineStyle: "dashed", lineColor: "#a855f7", width: 2 },
  imports: { lineStyle: "solid", lineColor: "#6b7280", width: 1 },
  calls: { lineStyle: "solid", lineColor: "#f59e0b", width: 1 },
  contains: { lineStyle: "dotted", lineColor: "#4b5563", width: 1 },
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
];

export function GraphView({
  graph,
  filters,
  selectedNodeId,
  onNodeSelect,
  onNodeDoubleClick,
}: GraphViewProps) {
  const cyRef = useRef<Core | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Convert graph data to Cytoscape elements
  const elements = useMemo(() => {
    const nodeElements = graph.nodes
      .filter((node) => {
        // Apply filters
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
      })
      .map((node) => ({
        data: {
          id: node.id,
          label: node.label,
          color: NODE_COLORS[node.type] || "#6b7280",
          shape: NODE_SHAPES[node.type] || "ellipse",
          size: getNodeSize(node),
          nodeType: node.type,
          ...node.metadata,
        },
      }));

    // Create a set of visible node IDs for edge filtering
    const visibleNodeIds = new Set(nodeElements.map((n) => n.data.id));

    const edgeElements = graph.edges
      .filter((edge) => visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target))
      .map((edge, index) => ({
        data: {
          id: `edge-${index}`,
          source: edge.source,
          target: edge.target,
          edgeType: edge.type,
          ...EDGE_STYLES[edge.type],
        },
      }));

    return [...nodeElements, ...edgeElements];
  }, [graph, filters]);

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

  // Fit graph when elements change significantly
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy || elements.length === 0) return;

    // Run layout
    const layout = cy.layout(getLayoutOptions("cose", elements.length));
    layout.run();
  }, [elements]);

  const handleCyInit = useCallback((cy: Core) => {
    cyRef.current = cy;

    // Node click handler
    cy.on("tap", "node", (event: EventObject) => {
      const nodeId = event.target.id();
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
  }, [onNodeSelect, onNodeDoubleClick]);

  const handleLayout = useCallback((layoutName: LayoutName) => {
    const cy = cyRef.current;
    if (!cy) return;

    const layout = cy.layout(getLayoutOptions(layoutName, elements.length));
    layout.run();
  }, [elements.length]);

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

  return (
    <div ref={containerRef} className="flex-1 relative bg-gray-900">
      {/* Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <div className="bg-gray-800 rounded-lg shadow-lg flex">
          <button
            onClick={() => handleLayout("cose")}
            className="px-3 py-2 text-sm text-gray-300 hover:bg-gray-700 rounded-l-lg"
            title="Force-directed layout"
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
            title="Fit to screen"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 8V4m0 0h4M4 4l5 5m11-1V4m0 0h-4m4 0l-5 5M4 16v4m0 0h4m-4 0l5-5m11 5l-5-5m5 5v-4m0 4h-4" />
            </svg>
          </button>
        </div>
      </div>

      {/* Legend */}
      <div className="absolute bottom-4 left-4 z-10 bg-gray-800 rounded-lg shadow-lg p-3">
        <h4 className="text-xs font-semibold text-gray-400 uppercase mb-2">Legend</h4>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {Object.entries(NODE_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span className="w-3 h-3 rounded" style={{ backgroundColor: color }} />
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

      {/* Graph */}
      {elements.length > 0 ? (
        <CytoscapeComponent
          elements={elements}
          stylesheet={stylesheet}
          cy={handleCyInit}
          style={{ width: "100%", height: "100%" }}
          wheelSensitivity={0.3}
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
}

function getNodeSize(node: GraphNode): number {
  switch (node.type) {
    case "package":
      return 50;
    case "class":
    case "interface":
      // Size based on method count if available
      const methodCount = node.metadata.methodCount || 0;
      return Math.min(60, Math.max(30, 30 + methodCount * 2));
    case "endpoint":
      return 25;
    case "file":
      return 20;
    default:
      return 30;
  }
}

function getLayoutOptions(name: LayoutName, nodeCount: number): LayoutOptions {
  const baseOptions = {
    name,
    animate: nodeCount < 100,
    animationDuration: 300,
  };

  switch (name) {
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
        numIter: 1000,
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
