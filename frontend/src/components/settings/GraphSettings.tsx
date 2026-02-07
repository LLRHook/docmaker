import { useSettings } from "../../contexts/SettingsContext";
import type { GraphViewSettings, EdgeType } from "../../types/settings";
import {
  LAYOUT_LABELS,
  LAYOUT_QUALITY_LABELS,
  NODE_SIZING_LABELS,
  EDGE_TYPE_LABELS,
  EDGE_TYPE_COLORS,
} from "../../types/settings";
import type { EdgeTypeFilters } from "../../types/settings";

export function GraphSettings() {
  const { settings, updateCategory } = useSettings();
  const graphView = settings.graphView;

  const handleScrollSpeedChange = (value: number) => {
    updateCategory("graphView", { scrollSpeed: value });
  };

  const handleZoomSensitivityChange = (value: number) => {
    updateCategory("graphView", { zoomSensitivity: value });
  };

  const handleLayoutChange = (value: GraphViewSettings["defaultLayout"]) => {
    updateCategory("graphView", { defaultLayout: value });
  };

  const handleAnimationSpeedChange = (value: GraphViewSettings["animationSpeed"]) => {
    updateCategory("graphView", { animationSpeed: value });
  };

  const handleShowLabelsChange = (value: boolean) => {
    updateCategory("graphView", { showLabels: value });
  };

  const handleLayoutQualityChange = (value: GraphViewSettings["layoutQuality"]) => {
    updateCategory("graphView", { layoutQuality: value });
  };

  const handleNodeSizingChange = (value: GraphViewSettings["nodeSizing"]) => {
    updateCategory("graphView", { nodeSizing: value });
  };

  const handleLargeGraphThresholdChange = (value: number) => {
    updateCategory("graphView", { largeGraphThreshold: value });
  };

  const handleEdgeTypeFilterChange = (edgeType: EdgeType, enabled: boolean) => {
    updateCategory("graphView", {
      edgeTypeFilters: { ...graphView.edgeTypeFilters, [edgeType]: enabled },
    });
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-100">Graph View Settings</h3>

      {/* Scroll Speed */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Scroll Speed
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0.1"
            max="1"
            step="0.05"
            value={graphView.scrollSpeed}
            onChange={(e) => handleScrollSpeedChange(parseFloat(e.target.value))}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-12 text-sm text-gray-400 text-right">
            {graphView.scrollSpeed.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>Slow</span>
          <span>Fast</span>
        </div>
      </div>

      {/* Zoom Sensitivity */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Zoom Sensitivity
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="0.1"
            max="0.5"
            step="0.05"
            value={graphView.zoomSensitivity}
            onChange={(e) => handleZoomSensitivityChange(parseFloat(e.target.value))}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-12 text-sm text-gray-400 text-right">
            {graphView.zoomSensitivity.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Default Layout */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Default Layout
        </label>
        <select
          value={graphView.defaultLayout}
          onChange={(e) =>
            handleLayoutChange(e.target.value as GraphViewSettings["defaultLayout"])
          }
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-sm text-sm text-gray-100 focus:outline-none focus:border-blue-500"
        >
          {Object.entries(LAYOUT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {/* Layout Quality */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Layout Quality
        </label>
        <select
          value={graphView.layoutQuality}
          onChange={(e) =>
            handleLayoutQualityChange(e.target.value as GraphViewSettings["layoutQuality"])
          }
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-sm text-sm text-gray-100 focus:outline-none focus:border-blue-500"
        >
          {Object.entries(LAYOUT_QUALITY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Higher quality produces better layouts but takes longer
        </p>
      </div>

      {/* Node Sizing */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Node Sizing
        </label>
        <select
          value={graphView.nodeSizing}
          onChange={(e) =>
            handleNodeSizingChange(e.target.value as GraphViewSettings["nodeSizing"])
          }
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-sm text-sm text-gray-100 focus:outline-none focus:border-blue-500"
        >
          {Object.entries(NODE_SIZING_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="text-xs text-gray-500 mt-1">
          Nodes with more connections appear larger when using "By Connection Count"
        </p>
      </div>

      {/* Large Graph Threshold */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Large Graph Threshold
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="50"
            max="500"
            step="25"
            value={graphView.largeGraphThreshold}
            onChange={(e) => handleLargeGraphThresholdChange(parseInt(e.target.value))}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-16 text-sm text-gray-400 text-right">
            {graphView.largeGraphThreshold} nodes
          </span>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Animations are disabled for graphs larger than this threshold
        </p>
      </div>

      {/* Animation Speed */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Animation Speed
        </label>
        <select
          value={graphView.animationSpeed}
          onChange={(e) =>
            handleAnimationSpeedChange(e.target.value as GraphViewSettings["animationSpeed"])
          }
          className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-sm text-sm text-gray-100 focus:outline-none focus:border-blue-500"
        >
          <option value="none">None (instant)</option>
          <option value="fast">Fast</option>
          <option value="normal">Normal</option>
          <option value="slow">Slow</option>
        </select>
      </div>

      {/* Show Labels */}
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="showLabels"
          checked={graphView.showLabels}
          onChange={(e) => handleShowLabelsChange(e.target.checked)}
          className="w-4 h-4 bg-gray-700 border-gray-600 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
        />
        <label htmlFor="showLabels" className="text-sm text-gray-300">
          Show Node Labels
        </label>
      </div>

      {/* Package Clustering */}
      <div className="flex items-center gap-3">
        <input
          type="checkbox"
          id="enablePackageClustering"
          checked={graphView.enablePackageClustering}
          onChange={(e) => updateCategory("graphView", { enablePackageClustering: e.target.checked })}
          className="w-4 h-4 bg-gray-700 border-gray-600 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
        />
        <label htmlFor="enablePackageClustering" className="text-sm text-gray-300">
          Group Nodes by Package
        </label>
      </div>
      <p className="text-xs text-gray-500 -mt-4 ml-7">
        Renders packages as compound nodes containing their classes and interfaces
      </p>

      {/* Default Edge Type Filters */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Default Edge Type Visibility
        </label>
        <div className="space-y-2">
          {(Object.keys(EDGE_TYPE_LABELS) as (keyof EdgeTypeFilters)[]).map((edgeType) => (
            <div key={edgeType} className="flex items-center gap-3">
              <input
                type="checkbox"
                id={`edge-${edgeType}`}
                checked={graphView.edgeTypeFilters[edgeType]}
                onChange={(e) => {
                  updateCategory("graphView", {
                    edgeTypeFilters: {
                      ...graphView.edgeTypeFilters,
                      [edgeType]: e.target.checked,
                    },
                  });
                }}
                className="w-4 h-4 bg-gray-700 border-gray-600 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
              />
              <span
                className="w-3 h-0.5 inline-block rounded"
                style={{ backgroundColor: EDGE_TYPE_COLORS[edgeType] }}
              />
              <label htmlFor={`edge-${edgeType}`} className="text-sm text-gray-300">
                {EDGE_TYPE_LABELS[edgeType]}
              </label>
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1">
          Controls which edge types are visible by default when loading a project
        </p>
      </div>
    </div>
  );
}
