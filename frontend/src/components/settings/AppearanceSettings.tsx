import { useSettings } from "../../contexts/SettingsContext";
import type { AppearanceSettings as AppearanceSettingsType } from "../../types/settings";

export function AppearanceSettings() {
  const { settings, updateCategory } = useSettings();
  const appearance = settings.appearance;

  const handleFontSizeChange = (value: AppearanceSettingsType["fontSize"]) => {
    updateCategory("appearance", { fontSize: value });
  };

  const handleUiScaleChange = (value: number) => {
    updateCategory("appearance", { uiScale: value });
  };

  const handleThemeChange = (value: AppearanceSettingsType["theme"]) => {
    updateCategory("appearance", { theme: value });
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-100">Appearance Settings</h3>

      {/* Theme */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Theme
        </label>
        <div className="flex gap-2">
          {(["dark", "light"] as const).map((theme) => (
            <button
              key={theme}
              onClick={() => handleThemeChange(theme)}
              className={`px-4 py-2 text-sm rounded-sm border flex items-center gap-2 ${
                appearance.theme === theme
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {theme === "dark" ? (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                </svg>
              )}
              {theme.charAt(0).toUpperCase() + theme.slice(1)}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Choose between dark and light color schemes
        </p>
      </div>

      {/* Font Size */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          Font Size
        </label>
        <div className="flex gap-2">
          {(["small", "medium", "large"] as const).map((size) => (
            <button
              key={size}
              onClick={() => handleFontSizeChange(size)}
              className={`px-4 py-2 text-sm rounded-sm border ${
                appearance.fontSize === size
                  ? "bg-blue-600 border-blue-500 text-white"
                  : "bg-gray-700 border-gray-600 text-gray-300 hover:bg-gray-600"
              }`}
            >
              {size.charAt(0).toUpperCase() + size.slice(1)}
            </button>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Affects text size throughout the application (12px / 14px / 16px)
        </p>
      </div>

      {/* UI Scale */}
      <div>
        <label className="block text-sm font-medium text-gray-300 mb-2">
          UI Scale
        </label>
        <div className="flex items-center gap-4">
          <input
            type="range"
            min="80"
            max="120"
            step="5"
            value={appearance.uiScale}
            onChange={(e) => handleUiScaleChange(parseInt(e.target.value))}
            className="flex-1 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />
          <span className="w-12 text-sm text-gray-400 text-right">
            {appearance.uiScale}%
          </span>
        </div>
        <div className="flex justify-between text-xs text-gray-500 mt-1">
          <span>80%</span>
          <span>100%</span>
          <span>120%</span>
        </div>
        <p className="text-xs text-gray-500 mt-2">
          Scales the entire interface (requires app restart to take full effect)
        </p>
      </div>
    </div>
  );
}
