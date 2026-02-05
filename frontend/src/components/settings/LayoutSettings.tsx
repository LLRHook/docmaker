import { useCallback } from "react";
import { useSettings } from "../../contexts/SettingsContext";
import { usePyloid } from "../../hooks/usePyloid";
import {
  WINDOW_PRESETS,
  MIN_SIDEBAR_WIDTH,
  MIN_DETAILS_PANEL_WIDTH,
  MAX_SIDEBAR_WIDTH,
  MAX_DETAILS_PANEL_WIDTH,
} from "../../types/settings";

export function LayoutSettings() {
  const { settings, updateCategory } = useSettings();
  const { resizeWindow, isAvailable } = usePyloid();
  const pyloidAvailable = isAvailable();

  const handlePresetClick = useCallback(
    async (width: number, height: number) => {
      updateCategory("layout", { windowWidth: width, windowHeight: height });
      if (pyloidAvailable) {
        await resizeWindow(width, height);
      }
    },
    [updateCategory, resizeWindow, pyloidAvailable]
  );

  const handleCustomSize = useCallback(
    async (dimension: "windowWidth" | "windowHeight", value: number) => {
      updateCategory("layout", { [dimension]: value });
      if (pyloidAvailable) {
        const newWidth = dimension === "windowWidth" ? value : settings.layout.windowWidth;
        const newHeight = dimension === "windowHeight" ? value : settings.layout.windowHeight;
        await resizeWindow(newWidth, newHeight);
      }
    },
    [updateCategory, resizeWindow, pyloidAvailable, settings.layout]
  );

  const handleSidebarWidth = useCallback(
    (value: number) => {
      const clamped = Math.min(MAX_SIDEBAR_WIDTH, Math.max(MIN_SIDEBAR_WIDTH, value));
      updateCategory("layout", { sidebarWidth: clamped });
    },
    [updateCategory]
  );

  const handleDetailsPanelWidth = useCallback(
    (value: number) => {
      const clamped = Math.min(MAX_DETAILS_PANEL_WIDTH, Math.max(MIN_DETAILS_PANEL_WIDTH, value));
      updateCategory("layout", { detailsPanelWidth: clamped });
    },
    [updateCategory]
  );

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-sm font-medium text-gray-200 mb-1">Layout</h3>
        <p className="text-xs text-gray-500 mb-4">
          Customize window size and panel dimensions
        </p>
      </div>

      {/* Window Size Presets */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Window Size Presets
        </label>
        <div className="grid grid-cols-2 gap-2">
          {WINDOW_PRESETS.map((preset) => {
            const isActive =
              settings.layout.windowWidth === preset.width &&
              settings.layout.windowHeight === preset.height;
            return (
              <button
                key={preset.label}
                onClick={() => handlePresetClick(preset.width, preset.height)}
                className={`px-3 py-2 text-sm rounded border transition-colors ${
                  isActive
                    ? "bg-blue-600 border-blue-500 text-white"
                    : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600 hover:border-gray-500"
                }`}
              >
                {preset.label}
              </button>
            );
          })}
        </div>
      </div>

      {/* Custom Window Size */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Custom Window Size
        </label>
        <div className="flex items-center gap-2">
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Width</label>
            <input
              type="number"
              value={settings.layout.windowWidth}
              onChange={(e) => handleCustomSize("windowWidth", parseInt(e.target.value) || 800)}
              min={800}
              max={3840}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            />
          </div>
          <span className="text-gray-500 pt-5">×</span>
          <div className="flex-1">
            <label className="block text-xs text-gray-500 mb-1">Height</label>
            <input
              type="number"
              value={settings.layout.windowHeight}
              onChange={(e) => handleCustomSize("windowHeight", parseInt(e.target.value) || 600)}
              min={600}
              max={2160}
              className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            />
          </div>
        </div>
        {!pyloidAvailable && (
          <p className="mt-2 text-xs text-yellow-500">
            Window resizing is only available in the desktop app
          </p>
        )}
      </div>

      {/* Sidebar Width */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Left Sidebar Width
          <span className="ml-2 text-gray-500 font-normal">{settings.layout.sidebarWidth}px</span>
        </label>
        <input
          type="range"
          min={MIN_SIDEBAR_WIDTH}
          max={MAX_SIDEBAR_WIDTH}
          value={settings.layout.sidebarWidth}
          onChange={(e) => handleSidebarWidth(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{MIN_SIDEBAR_WIDTH}px</span>
          <span>{MAX_SIDEBAR_WIDTH}px</span>
        </div>
      </div>

      {/* Details Panel Width */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Right Details Panel Width
          <span className="ml-2 text-gray-500 font-normal">{settings.layout.detailsPanelWidth}px</span>
        </label>
        <input
          type="range"
          min={MIN_DETAILS_PANEL_WIDTH}
          max={MAX_DETAILS_PANEL_WIDTH}
          value={settings.layout.detailsPanelWidth}
          onChange={(e) => handleDetailsPanelWidth(parseInt(e.target.value))}
          className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-600"
        />
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>{MIN_DETAILS_PANEL_WIDTH}px</span>
          <span>{MAX_DETAILS_PANEL_WIDTH}px</span>
        </div>
      </div>

      {/* Info about drag resizing */}
      <div className="p-3 bg-gray-700/50 rounded text-sm text-gray-400">
        <p className="flex items-start gap-2">
          <svg className="w-4 h-4 mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>
            You can also drag the edges of the sidebars to resize them directly in the main view.
          </span>
        </p>
      </div>
    </div>
  );
}
