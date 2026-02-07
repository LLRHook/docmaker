import { useSettings } from "../../contexts/SettingsContext";
import type { GraphViewSettings } from "../../types/settings";
import {
  LAYOUT_LABELS,
  LAYOUT_QUALITY_LABELS,
  NODE_SIZING_LABELS,
} from "../../types/settings";

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

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-c-text">Graph View Settings</h3>

      {/* Scroll Speed */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
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
            className="flex-1 h-2 bg-c-element rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-12 text-sm text-c-text-dim text-right">
            {graphView.scrollSpeed.toFixed(2)}
          </span>
        </div>
        <div className="flex justify-between text-xs text-c-text-faint mt-1">
          <span>Slow</span>
          <span>Fast</span>
        </div>
      </div>

      {/* Zoom Sensitivity */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
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
            className="flex-1 h-2 bg-c-element rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-12 text-sm text-c-text-dim text-right">
            {graphView.zoomSensitivity.toFixed(2)}
          </span>
        </div>
      </div>

      {/* Default Layout */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
          Default Layout
        </label>
        <select
          value={graphView.defaultLayout}
          onChange={(e) =>
            handleLayoutChange(e.target.value as GraphViewSettings["defaultLayout"])
          }
          className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
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
        <label className="block text-sm font-medium text-c-text-sub mb-2">
          Layout Quality
        </label>
        <select
          value={graphView.layoutQuality}
          onChange={(e) =>
            handleLayoutQualityChange(e.target.value as GraphViewSettings["layoutQuality"])
          }
          className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
        >
          {Object.entries(LAYOUT_QUALITY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="text-xs text-c-text-faint mt-1">
          Higher quality produces better layouts but takes longer
        </p>
      </div>

      {/* Node Sizing */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
          Node Sizing
        </label>
        <select
          value={graphView.nodeSizing}
          onChange={(e) =>
            handleNodeSizingChange(e.target.value as GraphViewSettings["nodeSizing"])
          }
          className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
        >
          {Object.entries(NODE_SIZING_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <p className="text-xs text-c-text-faint mt-1">
          Nodes with more connections appear larger when using "By Connection Count"
        </p>
      </div>

      {/* Large Graph Threshold */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
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
            className="flex-1 h-2 bg-c-element rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-16 text-sm text-c-text-dim text-right">
            {graphView.largeGraphThreshold} nodes
          </span>
        </div>
        <p className="text-xs text-c-text-faint mt-1">
          Animations are disabled for graphs larger than this threshold
        </p>
      </div>

      {/* Animation Speed */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
          Animation Speed
        </label>
        <select
          value={graphView.animationSpeed}
          onChange={(e) =>
            handleAnimationSpeedChange(e.target.value as GraphViewSettings["animationSpeed"])
          }
          className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
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
          className="w-4 h-4 bg-c-element border-c-line-soft rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
        />
        <label htmlFor="showLabels" className="text-sm text-c-text-sub">
          Show Node Labels
        </label>
      </div>
    </div>
  );
}
