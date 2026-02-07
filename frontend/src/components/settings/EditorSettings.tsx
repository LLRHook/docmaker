import { useSettings } from "../../contexts/SettingsContext";
import type { EditorSettings as EditorSettingsType } from "../../types/settings";
import { EDITOR_LABELS } from "../../types/settings";

export function EditorSettings() {
  const { settings, updateCategory } = useSettings();
  const editor = settings.editor;

  const handleEditorChange = (value: EditorSettingsType["preferredEditor"]) => {
    updateCategory("editor", { preferredEditor: value });
  };

  const handleCustomCommandChange = (value: string) => {
    updateCategory("editor", { customEditorCommand: value });
  };

  const handleAlwaysAskChange = (value: boolean) => {
    updateCategory("editor", { alwaysAsk: value });
  };

  const editorOptions: EditorSettingsType["preferredEditor"][] = [
    "auto",
    "vscode",
    "idea",
    "sublime",
    "system",
    "custom",
  ];

  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-c-text">Editor Integration</h3>

      {/* Preferred Editor */}
      <div>
        <label className="block text-sm font-medium text-c-text-sub mb-2">
          Preferred Editor
        </label>
        <select
          value={editor.preferredEditor}
          onChange={(e) =>
            handleEditorChange(e.target.value as EditorSettingsType["preferredEditor"])
          }
          className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
        >
          {editorOptions.map((opt) => (
            <option key={opt} value={opt}>
              {EDITOR_LABELS[opt]}
            </option>
          ))}
        </select>
        <p className="text-xs text-c-text-faint mt-2">
          The editor to use when opening files from the graph view
        </p>
      </div>

      {/* Custom Editor Command */}
      {editor.preferredEditor === "custom" && (
        <div>
          <label className="block text-sm font-medium text-c-text-sub mb-2">
            Custom Command
          </label>
          <input
            type="text"
            value={editor.customEditorCommand}
            onChange={(e) => handleCustomCommandChange(e.target.value)}
            placeholder="code --goto {file}:{line}"
            className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text placeholder-gray-500 focus:outline-none focus:border-blue-500"
          />
          <p className="text-xs text-c-text-faint mt-2">
            Use <code className="bg-c-element px-1 rounded">{"{file}"}</code> and{" "}
            <code className="bg-c-element px-1 rounded">{"{line}"}</code> as placeholders
          </p>
        </div>
      )}

      {/* Always Ask */}
      <div className="pt-4 border-t border-c-line">
        <div className="flex items-start gap-3">
          <input
            type="checkbox"
            id="alwaysAsk"
            checked={editor.alwaysAsk}
            onChange={(e) => handleAlwaysAskChange(e.target.checked)}
            className="mt-1 w-4 h-4 bg-c-element border-c-line-soft rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
          />
          <div>
            <label htmlFor="alwaysAsk" className="text-sm text-c-text-sub font-medium">
              Always ask before opening
            </label>
            <p className="text-xs text-c-text-faint mt-1">
              Shows an editor selection dialog each time you open a file, instead of using
              the preferred editor automatically
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
