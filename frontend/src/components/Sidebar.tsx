import { memo, useState, useMemo, useRef, useCallback, forwardRef, useImperativeHandle } from "react";
import type { GraphNode } from "../types/graph";
import { markStart, markEnd } from "../utils/perf";

interface SidebarProps {
  nodes: GraphNode[];
  onNodeSelect: (nodeId: string) => void;
  onFilterChange: (filters: FilterState) => void;
  selectedNodeId: string | null;
}

export interface FilterState {
  nodeTypes: Set<string>;
  categories: Set<string>;
  searchQuery: string;
}

const NODE_TYPES = [
  { id: "class", label: "Classes", color: "bg-blue-500" },
  { id: "interface", label: "Interfaces", color: "bg-purple-500" },
  { id: "endpoint", label: "Endpoints", color: "bg-green-500" },
  { id: "package", label: "Packages", color: "bg-gray-500" },
  { id: "file", label: "Files", color: "bg-orange-500" },
];

const CATEGORIES = [
  { id: "backend", label: "Backend", color: "bg-blue-500" },
  { id: "frontend", label: "Frontend", color: "bg-green-500" },
  { id: "config", label: "Config", color: "bg-amber-500" },
  { id: "test", label: "Test", color: "bg-gray-500" },
  { id: "unknown", label: "Unknown", color: "bg-gray-600" },
];

export interface SidebarHandle {
  focusSearch: () => void;
  getFilteredNodeIds: () => string[];
  toggleNodeType: (typeId: string) => void;
  clearSearch: () => void;
}

const COLLAPSED_KEY = "docmaker-sidebar-collapsed";

export const Sidebar = memo(forwardRef<SidebarHandle, SidebarProps>(function Sidebar({ nodes, onNodeSelect, onFilterChange, selectedNodeId }, ref) {
  const searchInputRef = useRef<HTMLInputElement>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeNodeTypes, setActiveNodeTypes] = useState<Set<string>>(
    new Set(NODE_TYPES.map((t) => t.id))
  );
  const [activeCategories, setActiveCategories] = useState<Set<string>>(
    new Set(CATEGORIES.map((c) => c.id))
  );
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(() => {
    try {
      const stored = localStorage.getItem(COLLAPSED_KEY);
      if (stored) return new Set(JSON.parse(stored) as string[]);
    } catch { /* ignore */ }
    return new Set();
  });

  // Expose imperative handle for keyboard navigation
  useImperativeHandle(ref, () => ({
    focusSearch() {
      searchInputRef.current?.focus();
    },
    getFilteredNodeIds() {
      return nodes
        .filter((node) => {
          if (!activeNodeTypes.has(node.type)) return false;
          const category = node.metadata.category || "unknown";
          if (!activeCategories.has(category)) return false;
          if (searchQuery) {
            const lowerQuery = searchQuery.toLowerCase();
            return (
              node.label.toLowerCase().includes(lowerQuery) ||
              (node.metadata.fqn?.toLowerCase().includes(lowerQuery) ?? false)
            );
          }
          return true;
        })
        .map((n) => n.id);
    },
    toggleNodeType(typeId: string) {
      toggleNodeType(typeId);
    },
    clearSearch() {
      setSearchQuery("");
      onFilterChange({
        nodeTypes: activeNodeTypes,
        categories: activeCategories,
        searchQuery: "",
      });
    },
  }), [nodes, activeNodeTypes, activeCategories, searchQuery, onFilterChange]);

  const toggleGroupCollapse = (groupId: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) {
        next.delete(groupId);
      } else {
        next.add(groupId);
      }
      try { localStorage.setItem(COLLAPSED_KEY, JSON.stringify([...next])); } catch { /* ignore */ }
      return next;
    });
  };

  const debounceTimer = useRef<ReturnType<typeof setTimeout>>(null);

  const handleSearchChange = useCallback((query: string) => {
    setSearchQuery(query);
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      onFilterChange({
        nodeTypes: activeNodeTypes,
        categories: activeCategories,
        searchQuery: query,
      });
    }, 200);
  }, [activeNodeTypes, activeCategories, onFilterChange]);

  const toggleNodeType = (typeId: string) => {
    const newTypes = new Set(activeNodeTypes);
    if (newTypes.has(typeId)) {
      newTypes.delete(typeId);
    } else {
      newTypes.add(typeId);
    }
    setActiveNodeTypes(newTypes);
    onFilterChange({
      nodeTypes: newTypes,
      categories: activeCategories,
      searchQuery,
    });
  };

  const toggleCategory = (categoryId: string) => {
    const newCategories = new Set(activeCategories);
    if (newCategories.has(categoryId)) {
      newCategories.delete(categoryId);
    } else {
      newCategories.add(categoryId);
    }
    setActiveCategories(newCategories);
    onFilterChange({
      nodeTypes: activeNodeTypes,
      categories: newCategories,
      searchQuery,
    });
  };

  // Filter and group nodes (memoized to avoid recalculation on unrelated renders)
  const { filteredNodes, nodesByType } = useMemo(() => {
    markStart("sidebar:filter");
    const filtered = nodes.filter((node) => {
      if (!activeNodeTypes.has(node.type)) return false;
      const category = node.metadata.category || "unknown";
      if (!activeCategories.has(category)) return false;
      if (searchQuery) {
        const lowerQuery = searchQuery.toLowerCase();
        return (
          node.label.toLowerCase().includes(lowerQuery) ||
          (node.metadata.fqn?.toLowerCase().includes(lowerQuery) ?? false)
        );
      }
      return true;
    });

    const grouped = NODE_TYPES.reduce(
      (acc, type) => {
        acc[type.id] = filtered.filter((n) => n.type === type.id);
        return acc;
      },
      {} as Record<string, GraphNode[]>
    );

    markEnd("sidebar:filter");
    return { filteredNodes: filtered, nodesByType: grouped };
  }, [nodes, activeNodeTypes, activeCategories, searchQuery]);

  return (
    <div className="w-full bg-gray-800 border-r border-gray-700 flex flex-col h-full">
      {/* Search */}
      <div className="p-3 border-b border-gray-700">
        <input
          ref={searchInputRef}
          type="text"
          placeholder="Search nodes..."
          value={searchQuery}
          onChange={(e) => handleSearchChange(e.target.value)}
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-sm text-sm text-gray-100 placeholder-gray-400 focus:outline-hidden focus:border-blue-500"
        />
      </div>

      {/* Filters */}
      <div className="p-3 border-b border-gray-700">
        <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Node Types</h3>
        <div className="flex flex-wrap gap-1">
          {NODE_TYPES.map((type) => (
            <button
              key={type.id}
              onClick={() => toggleNodeType(type.id)}
              className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                activeNodeTypes.has(type.id)
                  ? "bg-gray-600 text-gray-100"
                  : "bg-gray-700 text-gray-500"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${type.color}`} />
              {type.label}
            </button>
          ))}
        </div>
      </div>

      <div className="p-3 border-b border-gray-700">
        <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Categories</h3>
        <div className="flex flex-wrap gap-1">
          {CATEGORIES.map((cat) => (
            <button
              key={cat.id}
              onClick={() => toggleCategory(cat.id)}
              className={`px-2 py-1 text-xs rounded flex items-center gap-1 ${
                activeCategories.has(cat.id)
                  ? "bg-gray-600 text-gray-100"
                  : "bg-gray-700 text-gray-500"
              }`}
            >
              <span className={`w-2 h-2 rounded-full ${cat.color}`} />
              {cat.label}
            </button>
          ))}
        </div>
      </div>

      {/* Node List */}
      <div className="flex-1 overflow-y-auto">
        {NODE_TYPES.filter((type) => nodesByType[type.id]?.length > 0).map((type) => (
          <div key={type.id} className="border-b border-gray-700">
            <button
              onClick={() => toggleGroupCollapse(type.id)}
              className="w-full px-3 py-2 bg-gray-750 flex items-center gap-2 hover:bg-gray-700/50 transition-colors"
            >
              <svg
                className={`w-3 h-3 text-gray-400 transition-transform ${collapsedGroups.has(type.id) ? "" : "rotate-90"}`}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
              <span className={`w-2 h-2 rounded-full ${type.color}`} />
              <span className="text-xs font-semibold text-gray-300">
                {type.label} ({nodesByType[type.id].length})
              </span>
            </button>
            {!collapsedGroups.has(type.id) && (
              <div className="max-h-48 overflow-y-auto">
                {nodesByType[type.id].map((node) => (
                  <button
                    key={node.id}
                    onClick={() => onNodeSelect(node.id)}
                    className={`w-full px-3 py-1.5 text-left text-sm truncate hover:bg-gray-700 ${
                      selectedNodeId === node.id ? "bg-gray-700 text-blue-400" : "text-gray-300"
                    }`}
                    title={node.metadata.fqn || node.label}
                  >
                    {node.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Stats */}
      <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
        Showing {filteredNodes.length} of {nodes.length} nodes
      </div>
    </div>
  );
}));
