import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { GraphView, type GraphViewHandle } from "./components/GraphView";
import { Sidebar, type FilterState, type SidebarHandle } from "./components/Sidebar";
import { StatusBar } from "./components/StatusBar";
import { NodeDetails } from "./components/NodeDetails";
import { ResizablePanel } from "./components/ResizablePanel";
import { SettingsModal } from "./components/settings";
import { BreadcrumbTrail } from "./components/BreadcrumbTrail";
import { KeyboardShortcutHelp } from "./components/KeyboardShortcutHelp";
import { usePyloid } from "./hooks/usePyloid";
import { useSettings } from "./contexts/SettingsContext";
import { useNavigationHistory } from "./hooks/useNavigationHistory";
import { useKeyboardNavigation, type KeyboardNavigationCallbacks } from "./hooks/useKeyboardNavigation";
import type { CodeGraph, GraphNode } from "./types/graph";
import {
  MIN_SIDEBAR_WIDTH,
  MIN_DETAILS_PANEL_WIDTH,
  MAX_SIDEBAR_WIDTH,
  MAX_DETAILS_PANEL_WIDTH,
  MAX_RECENT_PROJECTS,
} from "./types/settings";
import type { RecentProject } from "./types/settings";
import { createLogger } from "./utils/logger";
import { markStart, markEnd, clearMetrics } from "./utils/perf";

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
  const [showSettings, setShowSettings] = useState(false);
  const [detailsPanelCollapsed, setDetailsPanelCollapsed] = useState(false);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const graphRef = useRef<GraphViewHandle>(null);
  const sidebarRef = useRef<SidebarHandle>(null);

  const { isAvailable, selectFolder, parseOnly, openFile, clearCaches } = usePyloid();
  const { settings, updateCategory } = useSettings();
  const navHistory = useNavigationHistory();

  // Check if running in Pyloid (now reactive)
  const pyloidAvailable = isAvailable();

  // Log app initialization and Pyloid availability changes
  useEffect(() => {
    logger.info("Pyloid availability changed:", pyloidAvailable);
  }, [pyloidAvailable]);

  const handleLoadProject = useCallback(async (path: string) => {
    logger.info("Loading project:", path);
    clearMetrics();
    markStart("app:projectLoad");
    clearCaches();
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
        markEnd("app:projectLoad");
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
      markEnd("app:projectLoad");

      // Save to lastProjectPath and update recent projects
      const projectName = path.split(/[/\\]/).filter(Boolean).pop() || path;
      const newRecent: RecentProject = {
        path,
        name: projectName,
        lastOpened: new Date().toISOString(),
      };
      const existing = settings.general.recentProjects.filter((p) => p.path !== path);
      const recentProjects = [newRecent, ...existing].slice(0, MAX_RECENT_PROJECTS);
      updateCategory("general", { lastProjectPath: path, recentProjects });
    } catch (err) {
      logger.error("Exception loading project:", err);
      setStatus("error");
      setStatusMessage(err instanceof Error ? err.message : "Unknown error");
      markEnd("app:projectLoad");
    }
  }, [parseOnly, updateCategory, clearCaches, settings.general.recentProjects]);

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
      // Auto-expand panel when selecting a node
      if (node) {
        setDetailsPanelCollapsed(false);
        // Push to navigation history
        navHistory.push({ nodeId: node.id, label: node.label, type: node.type });
      }
    } else {
      setDetailsNode(null);
    }
  }, [graph.nodes, navHistory]);

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

  const handleToggleDetailsPanel = useCallback(() => {
    setDetailsPanelCollapsed((prev) => !prev);
  }, []);

  const handleSidebarWidthChange = useCallback(
    (width: number) => {
      updateCategory("layout", { sidebarWidth: width });
    },
    [updateCategory]
  );

  const handleDetailsPanelWidthChange = useCallback(
    (width: number) => {
      updateCategory("layout", { detailsPanelWidth: width });
    },
    [updateCategory]
  );

  // Navigate to a node in the graph (for clickable links in details panel)
  const handleNavigateToNode = useCallback((nodeId: string) => {
    const node = graph.nodes.find((n) => n.id === nodeId);
    if (node) {
      setSelectedNodeId(nodeId);
      setDetailsNode(node);
      setDetailsPanelCollapsed(false);
      navHistory.push({ nodeId: node.id, label: node.label, type: node.type });
    }
  }, [graph.nodes, navHistory]);

  const handleOpenFile = useCallback(async (path: string, line: number) => {
    await openFile(path, line);
  }, [openFile]);

  // Breadcrumb callbacks
  const handleBreadcrumbGoBack = useCallback(() => {
    const entry = navHistory.goBack();
    if (entry) {
      handleNodeSelect(entry.nodeId);
      graphRef.current?.centerOnNode(entry.nodeId);
    }
  }, [navHistory, handleNodeSelect]);

  const handleBreadcrumbGoForward = useCallback(() => {
    const entry = navHistory.goForward();
    if (entry) {
      handleNodeSelect(entry.nodeId);
      graphRef.current?.centerOnNode(entry.nodeId);
    }
  }, [navHistory, handleNodeSelect]);

  const handleBreadcrumbGoTo = useCallback((index: number) => {
    const entry = navHistory.goTo(index);
    if (entry) {
      handleNodeSelect(entry.nodeId);
      graphRef.current?.centerOnNode(entry.nodeId);
    }
  }, [navHistory, handleNodeSelect]);

  // Keyboard navigation callbacks
  const NODE_TYPE_IDS = ["class", "interface", "endpoint", "package", "file"];

  const keyboardCallbacks: KeyboardNavigationCallbacks = useMemo(() => ({
    focusSearch: () => sidebarRef.current?.focusSearch(),
    clearSearch: () => sidebarRef.current?.clearSearch(),
    deselectNode: () => handleNodeSelect(null),
    fitGraph: () => graphRef.current?.fitGraph(),
    navigateConnected: (direction: "incoming" | "outgoing") => {
      if (!selectedNodeId || !graphRef.current) return;
      const connected = graphRef.current.getConnectedNodeIds(selectedNodeId);
      const ids = direction === "incoming" ? connected.incoming : connected.outgoing;
      if (ids.length > 0) {
        handleNodeSelect(ids[0]);
        graphRef.current.centerOnNode(ids[0]);
      }
    },
    nextSearchResult: () => {
      if (!sidebarRef.current) return;
      const ids = sidebarRef.current.getFilteredNodeIds();
      if (ids.length === 0) return;
      const currentIndex = selectedNodeId ? ids.indexOf(selectedNodeId) : -1;
      const nextIndex = (currentIndex + 1) % ids.length;
      handleNodeSelect(ids[nextIndex]);
      graphRef.current?.centerOnNode(ids[nextIndex]);
    },
    prevSearchResult: () => {
      if (!sidebarRef.current) return;
      const ids = sidebarRef.current.getFilteredNodeIds();
      if (ids.length === 0) return;
      const currentIndex = selectedNodeId ? ids.indexOf(selectedNodeId) : 0;
      const prevIndex = (currentIndex - 1 + ids.length) % ids.length;
      handleNodeSelect(ids[prevIndex]);
      graphRef.current?.centerOnNode(ids[prevIndex]);
    },
    toggleNodeType: (index: number) => {
      if (index >= 0 && index < NODE_TYPE_IDS.length) {
        sidebarRef.current?.toggleNodeType(NODE_TYPE_IDS[index]);
      }
    },
    goBack: handleBreadcrumbGoBack,
    goForward: handleBreadcrumbGoForward,
    toggleHelp: () => setShowKeyboardHelp((prev) => !prev),
  }), [selectedNodeId, handleNodeSelect, handleBreadcrumbGoBack, handleBreadcrumbGoForward]);

  useKeyboardNavigation(keyboardCallbacks);

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

  // Open last project on startup if enabled
  useEffect(() => {
    if (
      settings.general.openLastProjectOnStartup &&
      settings.general.lastProjectPath &&
      !projectPath
    ) {
      handleLoadProject(settings.general.lastProjectPath);
    }
    // Only run once on mount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Apply theme to document
  useEffect(() => {
    const theme = settings.appearance.theme;
    document.documentElement.setAttribute("data-theme", theme);
  }, [settings.appearance.theme]);

  // Keyboard shortcut: Ctrl+, to open settings
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === ",") {
        e.preventDefault();
        setShowSettings(true);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

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

        {/* Settings button */}
        <button
          onClick={() => setShowSettings(true)}
          className="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded"
          title="Settings (Ctrl+,)"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
            />
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
            />
          </svg>
        </button>

        {/* Keyboard help button */}
        <button
          onClick={() => setShowKeyboardHelp(true)}
          className="p-2 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded"
          title="Keyboard shortcuts (?)"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </button>

        {!pyloidAvailable && (
          <span className="text-xs text-yellow-500 bg-yellow-900/30 px-2 py-1 rounded-sm">
            Dev Mode
          </span>
        )}
      </header>

      {/* Breadcrumb Trail */}
      <BreadcrumbTrail
        entries={navHistory.entries}
        cursor={navHistory.cursor}
        canGoBack={navHistory.canGoBack}
        canGoForward={navHistory.canGoForward}
        onGoBack={handleBreadcrumbGoBack}
        onGoForward={handleBreadcrumbGoForward}
        onGoTo={handleBreadcrumbGoTo}
        onClear={navHistory.clear}
      />

      {/* Main content */}
      {status === "idle" || status === "error" ? (
        /* Landing screen */
        <div className="flex-1 flex items-center justify-center overflow-hidden">
          <div className="text-center max-w-md">
            <svg className="w-16 h-16 mx-auto mb-4 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
            </svg>
            <h2 className="text-xl font-semibold text-gray-300 mb-2">Open a project to get started</h2>
            <p className="text-sm text-gray-500 mb-6">
              Browse for a folder or drag and drop one here
            </p>
            <button
              onClick={handleBrowseFolder}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-sm inline-flex items-center gap-2"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              Open Project
            </button>

            {status === "error" && statusMessage && (
              <div className="mt-4 p-3 bg-red-900/30 border border-red-800 rounded text-sm text-red-300">
                {statusMessage}
              </div>
            )}

            {/* Recent projects */}
            {settings.general.recentProjects.length > 0 && (
              <div className="mt-8 text-left">
                <h3 className="text-sm font-medium text-gray-400 mb-3">Recent Projects</h3>
                <div className="space-y-1">
                  {settings.general.recentProjects.map((project) => (
                    <button
                      key={project.path}
                      onClick={() => handleLoadProject(project.path)}
                      className="w-full text-left px-3 py-2 rounded hover:bg-gray-800 group transition-colors"
                    >
                      <div className="text-sm text-gray-300 group-hover:text-gray-100 truncate">
                        {project.name}
                      </div>
                      <div className="text-xs text-gray-600 truncate">
                        {project.path}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : status === "scanning" || status === "parsing" ? (
        /* Loading state */
        <div className="flex-1 flex items-center justify-center overflow-hidden">
          <div className="text-center">
            <svg className="w-8 h-8 mx-auto mb-3 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
            <p className="text-sm text-gray-400">{statusMessage}</p>
          </div>
        </div>
      ) : (
        /* Graph workspace */
        <div className="flex-1 flex overflow-hidden">
          {/* Resizable Sidebar */}
          <ResizablePanel
            width={settings.layout.sidebarWidth}
            minWidth={MIN_SIDEBAR_WIDTH}
            maxWidth={MAX_SIDEBAR_WIDTH}
            onWidthChange={handleSidebarWidthChange}
            side="left"
          >
            <Sidebar
              ref={sidebarRef}
              nodes={graph.nodes}
              onNodeSelect={handleNodeSelect}
              onFilterChange={setFilters}
              selectedNodeId={selectedNodeId}
            />
          </ResizablePanel>

          {/* Graph view */}
          <GraphView
            ref={graphRef}
            graph={graph}
            filters={filters}
            selectedNodeId={selectedNodeId}
            onNodeSelect={handleNodeSelect}
            onNodeDoubleClick={handleNodeDoubleClick}
          />

          {/* Resizable Details panel */}
          {!detailsPanelCollapsed ? (
            <ResizablePanel
              width={settings.layout.detailsPanelWidth}
              minWidth={MIN_DETAILS_PANEL_WIDTH}
              maxWidth={MAX_DETAILS_PANEL_WIDTH}
              onWidthChange={handleDetailsPanelWidthChange}
              side="right"
            >
              <NodeDetails
                node={detailsNode}
                isCollapsed={detailsPanelCollapsed}
                onToggleCollapse={handleToggleDetailsPanel}
                onClose={handleCloseDetails}
                onOpenFile={handleOpenFile}
                onNavigateToNode={handleNavigateToNode}
                allNodes={graph.nodes}
              />
            </ResizablePanel>
          ) : (
            <NodeDetails
              node={detailsNode}
              isCollapsed={detailsPanelCollapsed}
              onToggleCollapse={handleToggleDetailsPanel}
              onClose={handleCloseDetails}
              onOpenFile={handleOpenFile}
              onNavigateToNode={handleNavigateToNode}
              allNodes={graph.nodes}
            />
          )}
        </div>
      )}

      {/* Status bar */}
      <StatusBar
        projectPath={projectPath}
        stats={stats}
        status={status}
        message={statusMessage}
      />

      {/* Settings modal */}
      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />

      {/* Keyboard shortcut help overlay */}
      <KeyboardShortcutHelp isOpen={showKeyboardHelp} onClose={() => setShowKeyboardHelp(false)} />
    </div>
  );
}
