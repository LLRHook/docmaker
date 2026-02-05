import { useSettings } from "../../contexts/SettingsContext";

export function GeneralSettings() {
  const { settings, updateCategory } = useSettings();
  const general = settings.general;

  const handleOpenLastProjectChange = (value: boolean) => {
    updateCategory("general", { openLastProjectOnStartup: value });
  };

  const handleClearLastProject = () => {
    updateCategory("general", { lastProjectPath: null });
  };

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-gray-100">General Settings</h3>

      {/* Open Last Project on Startup */}
      <div>
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="openLastProject"
            checked={general.openLastProjectOnStartup}
            onChange={(e) => handleOpenLastProjectChange(e.target.checked)}
            className="mt-1 w-4 h-4 bg-gray-700 border-gray-600 rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <div>
            <label htmlFor="openLastProject" className="text-sm text-gray-300 font-medium">
              Open last project on startup
            </label>
            <p className="text-xs text-gray-500 mt-1">
              Automatically load the most recently opened project when the application starts
            </p>
          </div>
        </div>
      </div>

      {/* Last Project Path */}
      {general.lastProjectPath && (
        <div className="p-3 bg-gray-700/50 rounded-sm">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-400">Last opened project:</p>
              <p className="text-sm text-gray-300 font-mono truncate max-w-xs">
                {general.lastProjectPath}
              </p>
            </div>
            <button
              onClick={handleClearLastProject}
              className="px-2 py-1 text-xs text-gray-400 hover:text-gray-200 hover:bg-gray-600 rounded"
            >
              Clear
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
