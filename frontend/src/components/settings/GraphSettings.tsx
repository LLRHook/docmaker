import { useSettings } from "../../contexts/SettingsContext";
import type { GraphViewSettings } from "../../types/settings";

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
          <option value="cose">Force-directed (CoSE)</option>
          <option value="circle">Circular</option>
          <option value="grid">Grid</option>
        </select>
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
    </div>
  );
}
