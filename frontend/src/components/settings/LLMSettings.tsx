import { useState, useCallback } from "react";
import { useSettings } from "../../contexts/SettingsContext";
import { usePyloid } from "../../hooks/usePyloid";
import type { LLMProvider } from "../../types/settings";
import { LLM_PROVIDER_LABELS } from "../../types/settings";

const PROVIDER_OPTIONS: LLMProvider[] = ["ollama", "lmstudio", "openai", "anthropic"];

function needsBaseUrl(provider: LLMProvider): boolean {
  return provider === "ollama" || provider === "lmstudio";
}

function needsApiKey(provider: LLMProvider): boolean {
  return provider === "openai" || provider === "anthropic";
}

export function LLMSettings() {
  const { settings, updateCategory } = useSettings();
  const { detectOllama, testLlmConnection } = usePyloid();
  const llm = settings.llm;

  // Key resets test state when LLM settings change
  const settingsKey = `${llm.provider}:${llm.model}:${llm.baseUrl}:${llm.apiKey}`;
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [testError, setTestError] = useState<string | null>(null);
  const [prevSettingsKey, setPrevSettingsKey] = useState(settingsKey);
  const [detectedModels, setDetectedModels] = useState<string[]>([]);
  const [detecting, setDetecting] = useState(false);

  // Reset test status when settings change (React-idiomatic state reset)
  if (settingsKey !== prevSettingsKey) {
    setPrevSettingsKey(settingsKey);
    setTestStatus("idle");
    setTestError(null);
  }

  const handleTestConnection = useCallback(async () => {
    setTestStatus("testing");
    setTestError(null);
    const result = await testLlmConnection(llm);
    if (result.success) {
      setTestStatus("success");
    } else {
      setTestStatus("error");
      setTestError(result.error || "Connection failed");
    }
  }, [llm, testLlmConnection]);

  const handleDetectOllama = useCallback(async () => {
    setDetecting(true);
    const result = await detectOllama(llm.baseUrl);
    setDetectedModels(result.models);
    if (result.available && result.models.length > 0 && !llm.model) {
      updateCategory("llm", { model: result.models[0] });
    }
    setDetecting(false);
  }, [llm.baseUrl, llm.model, detectOllama, updateCategory]);


  return (
    <div className="space-y-6">
      <h3 className="text-lg font-medium text-c-text">LLM Configuration</h3>

      {/* Enable/Disable Toggle */}
      <div className="flex items-start gap-3">
        <input
          type="checkbox"
          id="llmEnabled"
          checked={llm.enabled}
          onChange={(e) => updateCategory("llm", { enabled: e.target.checked })}
          className="mt-1 w-4 h-4 bg-c-element border-c-line-soft rounded text-blue-500 focus:ring-blue-500 focus:ring-offset-gray-800"
        />
        <div>
          <label htmlFor="llmEnabled" className="text-sm text-c-text-sub font-medium">
            Enable LLM classification
          </label>
          <p className="text-xs text-c-text-faint mt-1">
            Use an LLM to intelligently classify source files during project scanning
          </p>
        </div>
      </div>

      {llm.enabled && (
        <>
          {/* Provider */}
          <div>
            <label className="block text-sm font-medium text-c-text-sub mb-2">
              Provider
            </label>
            <select
              value={llm.provider}
              onChange={(e) => updateCategory("llm", { provider: e.target.value as LLMProvider })}
              className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
            >
              {PROVIDER_OPTIONS.map((p) => (
                <option key={p} value={p}>
                  {LLM_PROVIDER_LABELS[p]}
                </option>
              ))}
            </select>
          </div>

          {/* Model */}
          <div>
            <label className="block text-sm font-medium text-c-text-sub mb-2">
              Model
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={llm.model}
                onChange={(e) => updateCategory("llm", { model: e.target.value })}
                placeholder="llama3.2"
                className="flex-1 px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              {llm.provider === "ollama" && (
                <button
                  onClick={handleDetectOllama}
                  disabled={detecting}
                  className="px-3 py-2 text-sm bg-c-element border border-c-line-soft rounded-sm text-c-text-sub hover:text-c-text hover:border-blue-500 transition-colors disabled:opacity-50"
                >
                  {detecting ? "Detecting..." : "Detect Models"}
                </button>
              )}
            </div>
            {detectedModels.length > 0 && llm.provider === "ollama" && (
              <div className="mt-2 flex flex-wrap gap-1.5">
                {detectedModels.map((m) => (
                  <button
                    key={m}
                    onClick={() => updateCategory("llm", { model: m })}
                    className={`px-2 py-1 text-xs rounded border transition-colors ${
                      m === llm.model
                        ? "bg-blue-600/20 border-blue-500 text-blue-400"
                        : "bg-c-element border-c-line-soft text-c-text-dim hover:text-c-text hover:border-c-line"
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Base URL (for local providers) */}
          {needsBaseUrl(llm.provider) && (
            <div>
              <label className="block text-sm font-medium text-c-text-sub mb-2">
                Base URL
              </label>
              <input
                type="text"
                value={llm.baseUrl}
                onChange={(e) => updateCategory("llm", { baseUrl: e.target.value })}
                placeholder="http://localhost:11434"
                className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
            </div>
          )}

          {/* API Key (for cloud providers) */}
          {needsApiKey(llm.provider) && (
            <div>
              <label className="block text-sm font-medium text-c-text-sub mb-2">
                API Key
              </label>
              <input
                type="password"
                value={llm.apiKey}
                onChange={(e) => updateCategory("llm", { apiKey: e.target.value })}
                placeholder="sk-..."
                className="w-full px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text placeholder-gray-500 focus:outline-none focus:border-blue-500"
              />
              <p className="text-xs text-c-text-faint mt-2">
                Your API key is stored locally and never sent to our servers
              </p>
            </div>
          )}

          {/* Timeout */}
          <div>
            <label className="block text-sm font-medium text-c-text-sub mb-2">
              Timeout (seconds)
            </label>
            <input
              type="number"
              value={llm.timeout}
              onChange={(e) => updateCategory("llm", { timeout: Math.max(1, parseInt(e.target.value) || 30) })}
              min={1}
              max={300}
              className="w-24 px-3 py-2 bg-c-element border border-c-line-soft rounded-sm text-sm text-c-text focus:outline-none focus:border-blue-500"
            />
          </div>

          {/* Test Connection */}
          <div className="pt-4 border-t border-c-line">
            <div className="flex items-center gap-3">
              <button
                onClick={handleTestConnection}
                disabled={testStatus === "testing"}
                className="px-4 py-2 text-sm bg-c-element border border-c-line-soft rounded-sm text-c-text-sub hover:text-c-text hover:border-blue-500 transition-colors disabled:opacity-50"
              >
                {testStatus === "testing" ? "Testing..." : "Test Connection"}
              </button>
              {testStatus === "success" && (
                <span className="flex items-center gap-1.5 text-sm text-green-400">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Connected
                </span>
              )}
              {testStatus === "error" && (
                <span className="text-sm text-red-400">
                  {testError}
                </span>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
