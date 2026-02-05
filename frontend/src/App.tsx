import { useState, useCallback, useEffect } from "react";
import { GraphView } from "./components/GraphView";
import { Sidebar, type FilterState } from "./components/Sidebar";
import { StatusBar } from "./components/StatusBar";
import { NodeDetails } from "./components/NodeDetails";
import { usePyloid } from "./hooks/usePyloid";
import type { CodeGraph, GraphNode } from "./types/graph";

type AppStatus = "idle" | "scanning" | "parsing" | "generating" | "ready" | "error";

export function App() {
  const [projectPath, setProjectPath] = useState<string | null>(null);
  const [graph, setGraph] = useState<CodeGraph>({ nodes: [], edges: [] });
  const [status, setStatus] = useState<AppStatus>("idle");
  const [statusMessage, setStatusMessage] = useState<string>("");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [detailsNode, setDetailsNode] = useState<GraphNode | null>(null);
  const [stats, setStats] = useState<{ files: number; classes: number; endpoints: number } | null>(null);
  const [filters, setFilters] = useState<FilterState>({
    nodeTypes: new Set(["class", "interface", "endpoint", "package", "file"]),
    categories: new Set(["backend", "frontend", "config", "test", "unknown"]),
    searchQuery: "",
  });

  const { isAvailable, parseOnly, openFile } = usePyloid();

  // Check if running in Pyloid
  const pyloidAvailable = isAvailable();

  const handleSelectFolder = useCallback(async () => {
    if (!pyloidAvailable) {
      // In development without Pyloid, use a prompt
      const path = prompt("Enter project path:");
      if (path) {
        await handleLoadProject(path);
      }
      return;
    }

    // Use native folder picker via IPC
    // For now, use prompt as fallback
    const path = prompt("Enter project path:");
    if (path) {
      await handleLoadProject(path);
    }
  }, [pyloidAvailable]);

  const handleLoadProject = useCallback(async (path: string) => {
    setStatus("scanning");
    setStatusMessage("Scanning project files...");

    try {
      setStatus("parsing");
      setStatusMessage("Parsing source files...");

      const result = await parseOnly(path);

      if (result.error) {
        setStatus("error");
        setStatusMessage(result.error);
        return;
      }

      setProjectPath(path);
      setGraph(result.graph);
      setStats({
        files: result.stats.filesParsed,
        classes: result.stats.classesFound,
        endpoints: result.stats.endpointsFound,
      });
      setStatus("ready");
      setStatusMessage(`Loaded ${result.stats.classesFound} classes, ${result.stats.endpointsFound} endpoints`);
    } catch (err) {
      setStatus("error");
      setStatusMessage(err instanceof Error ? err.message : "Unknown error");
    }
  }, [parseOnly]);

  const handleNodeSelect = useCallback((nodeId: string | null) => {
    setSelectedNodeId(nodeId);
    if (nodeId) {
      const node = graph.nodes.find((n) => n.id === nodeId);
      setDetailsNode(node || null);
    } else {
      setDetailsNode(null);
    }
  }, [graph.nodes]);

  const handleNodeDoubleClick = useCallback(async (node: GraphNode) => {
    const path = node.metadata.path || node.metadata.filePath;
    const line = node.metadata.line || 0;
    if (path) {
      await openFile(path, line);
    }
  }, [openFile]);

  const handleCloseDetails = useCallback(() => {
    setDetailsNode(null);
    setSelectedNodeId(null);
  }, []);

  const handleOpenFile = useCallback(async (path: string, line: number) => {
    await openFile(path, line);
  }, [openFile]);

  // Handle project load from CLI argument
  useEffect(() => {
    // Check for load-project event from Pyloid
    const handleLoadProjectEvent = (event: CustomEvent<{ path: string }>) => {
      handleLoadProject(event.detail.path);
    };

    window.addEventListener("load-project" as keyof WindowEventMap, handleLoadProjectEvent as EventListener);
    return () => {
      window.removeEventListener("load-project" as keyof WindowEventMap, handleLoadProjectEvent as EventListener);
    };
  }, [handleLoadProject]);

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-gray-100">
      {/* Header */}
      <header className="h-12 bg-gray-800 border-b border-gray-700 flex items-center px-4 gap-4">
        <h1 className="font-semibold text-lg">Docmaker</h1>

        <div className="flex-1" />

        <button
          onClick={handleSelectFolder}
          className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded flex items-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          Open Project
        </button>

        {!pyloidAvailable && (
          <span className="text-xs text-yellow-500 bg-yellow-900/30 px-2 py-1 rounded">
            Dev Mode
          </span>
        )}
      </header>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <Sidebar
          nodes={graph.nodes}
          onNodeSelect={handleNodeSelect}
          onFilterChange={setFilters}
          selectedNodeId={selectedNodeId}
        />

        {/* Graph view */}
        <GraphView
          graph={graph}
          filters={filters}
          selectedNodeId={selectedNodeId}
          onNodeSelect={handleNodeSelect}
          onNodeDoubleClick={handleNodeDoubleClick}
        />

        {/* Details panel */}
        {detailsNode && (
          <NodeDetails
            node={detailsNode}
            onClose={handleCloseDetails}
            onOpenFile={handleOpenFile}
          />
        )}
      </div>

      {/* Status bar */}
      <StatusBar
        projectPath={projectPath}
        stats={stats}
        status={status}
        message={statusMessage}
      />
    </div>
  );
}
