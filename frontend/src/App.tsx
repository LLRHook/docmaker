import { useState, useCallback, useEffect, useRef } from "react";
import { GraphView } from "./components/GraphView";
import { Sidebar, type FilterState } from "./components/Sidebar";
import { StatusBar } from "./components/StatusBar";
import { NodeDetails } from "./components/NodeDetails";
import { usePyloid } from "./hooks/usePyloid";
import type { CodeGraph, GraphNode } from "./types/graph";
import { createLogger } from "./utils/logger";

const logger = createLogger("App");

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
  const [showOpenMenu, setShowOpenMenu] = useState(false);
  const [showPathInput, setShowPathInput] = useState(false);
  const [pathInputValue, setPathInputValue] = useState("");
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const { isAvailable, selectFolder, parseOnly, openFile } = usePyloid();

  // Check if running in Pyloid (now reactive)
  const pyloidAvailable = isAvailable();

  // Log app initialization and Pyloid availability changes
  useEffect(() => {
    logger.info("Pyloid availability changed:", pyloidAvailable);
  }, [pyloidAvailable]);

  const handleLoadProject = useCallback(async (path: string) => {
    logger.info("Loading project:", path);
    setStatus("scanning");
    setStatusMessage("Scanning project files...");

    try {
      setStatus("parsing");
      setStatusMessage("Parsing source files...");

      const result = await parseOnly(path);

      if (result.error) {
        logger.error("Failed to load project:", result.error);
        setStatus("error");
        setStatusMessage(result.error);
        return;
      }

      logger.info("Project loaded successfully:", result.stats);
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
      logger.error("Exception loading project:", err);
      setStatus("error");
      setStatusMessage(err instanceof Error ? err.message : "Unknown error");
    }
  }, [parseOnly]);

  const handleBrowseFolder = useCallback(async () => {
    setShowOpenMenu(false);

    // Try native folder picker first
    const path = await selectFolder();
    if (path) {
      await handleLoadProject(path);
      return;
    }

    // Fallback to prompt if native picker not available or cancelled
    if (!pyloidAvailable) {
      const manualPath = prompt("Enter project path:");
      if (manualPath) {
        await handleLoadProject(manualPath);
      }
    }
  }, [pyloidAvailable, selectFolder, handleLoadProject]);

  const handleShowPathInput = useCallback(() => {
    setShowOpenMenu(false);
    setShowPathInput(true);
    setPathInputValue("");
  }, []);

  const handlePathInputSubmit = useCallback(async () => {
    if (pathInputValue.trim()) {
      setShowPathInput(false);
      await handleLoadProject(pathInputValue.trim());
    }
  }, [pathInputValue, handleLoadProject]);

  const handlePathInputKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      handlePathInputSubmit();
    } else if (e.key === "Escape") {
      setShowPathInput(false);
    }
  }, [handlePathInputSubmit]);

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setShowOpenMenu(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Focus input when shown
  useEffect(() => {
    if (showPathInput && inputRef.current) {
      inputRef.current.focus();
    }
  }, [showPathInput]);

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

        <div className="relative" ref={menuRef}>
          <button
            onClick={() => setShowOpenMenu(!showOpenMenu)}
            className="px-4 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-sm flex items-center gap-2"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            Open Project
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </button>

          {showOpenMenu && (
            <div className="absolute right-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-sm shadow-lg z-50">
              <button
                onClick={handleBrowseFolder}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 19a2 2 0 01-2-2V7a2 2 0 012-2h4l2 2h4a2 2 0 012 2v1M5 19h14a2 2 0 002-2v-5a2 2 0 00-2-2H9a2 2 0 00-2 2v5a2 2 0 01-2 2z" />
                </svg>
                Browse...
              </button>
              <button
                onClick={handleShowPathInput}
                className="w-full px-4 py-2 text-left text-sm hover:bg-gray-700 flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                </svg>
                Enter path...
              </button>
            </div>
          )}
        </div>

        {/* Path input modal */}
        {showPathInput && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
            <div className="bg-gray-800 border border-gray-700 rounded-lg p-4 w-96 shadow-xl">
              <h3 className="text-sm font-medium mb-3">Enter project path</h3>
              <input
                ref={inputRef}
                type="text"
                value={pathInputValue}
                onChange={(e) => setPathInputValue(e.target.value)}
                onKeyDown={handlePathInputKeyDown}
                placeholder="C:\path\to\project"
                className="w-full px-3 py-2 bg-gray-900 border border-gray-600 rounded-sm text-sm focus:outline-hidden focus:border-blue-500"
              />
              <div className="flex justify-end gap-2 mt-3">
                <button
                  onClick={() => setShowPathInput(false)}
                  className="px-3 py-1.5 text-sm text-gray-400 hover:text-gray-200"
                >
                  Cancel
                </button>
                <button
                  onClick={handlePathInputSubmit}
                  className="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-sm"
                >
                  Open
                </button>
              </div>
            </div>
          </div>
        )}

        {!pyloidAvailable && (
          <span className="text-xs text-yellow-500 bg-yellow-900/30 px-2 py-1 rounded-sm">
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
