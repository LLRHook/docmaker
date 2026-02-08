import { useState, useCallback, useRef, useEffect } from "react";
import { usePyloid } from "../hooks/usePyloid";
import { useSettings } from "../contexts/SettingsContext";
import { GraphView, type GraphViewHandle } from "./GraphView";
import type { CodeGraph } from "../types/graph";
import type { LLMProvider } from "../types/settings";
import { LLM_PROVIDER_LABELS, DEFAULT_SETTINGS } from "../types/settings";
import type { FilterState } from "./Sidebar";

type WizardStep = "welcome" | "llmSetup" | "scanning" | "results" | "explore";

interface OnboardingWizardProps {
  onComplete: (projectPath: string, graph: CodeGraph, stats: { files: number; classes: number; endpoints: number }) => void;
  onSkip: () => void;
}

export function OnboardingWizard({ onComplete, onSkip }: OnboardingWizardProps) {
  const [step, setStep] = useState<WizardStep>("welcome");
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [scanStatus, setScanStatus] = useState<string>("");
  const [scanError, setScanError] = useState<string | null>(null);
  const [parsedGraph, setParsedGraph] = useState<CodeGraph>({ nodes: [], edges: [] });
  const [parsedStats, setParsedStats] = useState<{ files: number; classes: number; endpoints: number } | null>(null);
  const [showTips, setShowTips] = useState(true);
  const graphRef = useRef<GraphViewHandle>(null);
  const pathInputRef = useRef<HTMLInputElement>(null);
  const [showPathInput, setShowPathInput] = useState(false);
  const [pathInputValue, setPathInputValue] = useState("");

  const { isAvailable, selectFolder, parseOnly, detectOllama, testLlmConnection } = usePyloid();
  const { updateCategory } = useSettings();
  const pyloidAvailable = isAvailable();

  const defaultFilters: FilterState = {
    nodeTypes: new Set(["class", "interface", "endpoint", "package", "file"]),
    categories: new Set(["backend", "frontend", "config", "test", "unknown"]),
    edgeTypes: new Set(["extends", "implements", "imports", "calls", "contains"]),
    searchQuery: "",
  };

  // Focus path input when shown
  useEffect(() => {
    if (showPathInput && pathInputRef.current) {
      pathInputRef.current.focus();
    }
  }, [showPathInput]);

  // Auto-fit graph when entering explore step
  useEffect(() => {
    if (step === "explore" && graphRef.current) {
      const timer = setTimeout(() => graphRef.current?.fitGraph(), 300);
      return () => clearTimeout(timer);
    }
  }, [step]);

  const handleSelectFolder = useCallback(async () => {
    const path = await selectFolder();
    if (path) {
      setSelectedPath(path);
      setStep("llmSetup");
    }
  }, [selectFolder]);

  const handleManualPath = useCallback(() => {
    setShowPathInput(true);
    setPathInputValue("");
  }, []);

  const handlePathSubmit = useCallback(async () => {
    const path = pathInputValue.trim();
    if (path) {
      setShowPathInput(false);
      setSelectedPath(path);
      setStep("llmSetup");
    }
  }, [pathInputValue]);

  const handleParse = useCallback(async (path: string) => {
    setStep("scanning");
    setScanStatus("Scanning project files...");
    setScanError(null);

    try {
      setScanStatus("Parsing source files...");
      const result = await parseOnly(path);

      if (result.error) {
        setScanError(result.error);
        setScanStatus("");
        return;
      }

      setParsedGraph(result.graph);
      setParsedStats({
        files: result.stats.filesParsed,
        classes: result.stats.classesFound,
        endpoints: result.stats.endpointsFound,
      });
      setScanStatus("");
      setStep("results");
    } catch (err) {
      setScanError(err instanceof Error ? err.message : "Unknown error");
      setScanStatus("");
    }
  }, [parseOnly]);

  const handleFinish = useCallback(() => {
    if (selectedPath && parsedGraph && parsedStats) {
      updateCategory("general", { firstRunCompleted: true, lastProjectPath: selectedPath });
      onComplete(selectedPath, parsedGraph, parsedStats);
    }
  }, [selectedPath, parsedGraph, parsedStats, updateCategory, onComplete]);

  const handleSkip = useCallback(() => {
    updateCategory("general", { firstRunCompleted: true });
    onSkip();
  }, [updateCategory, onSkip]);

  const handleRetry = useCallback(() => {
    setStep("welcome");
    setSelectedPath(null);
    setScanError(null);
    setScanStatus("");
    setParsedGraph({ nodes: [], edges: [] });
    setParsedStats(null);
  }, []);

  return (
    <div className="fixed inset-0 bg-gray-900 z-50 flex flex-col">
      {/* Progress indicator */}
      <div className="h-1 bg-gray-800">
        <div
          className="h-full bg-blue-500 transition-all duration-500"
          style={{
            width: step === "welcome" ? "20%" : step === "llmSetup" ? "40%" : step === "scanning" ? "60%" : step === "results" ? "80%" : "100%",
          }}
        />
      </div>

      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          </div>
          <span className="font-semibold text-lg text-gray-100">Docmaker</span>
        </div>
        <button
          onClick={handleSkip}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          Skip setup
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 flex items-center justify-center overflow-hidden">
        {step === "welcome" && (
          <WelcomeStep
            pyloidAvailable={pyloidAvailable}
            onBrowse={handleSelectFolder}
            onManualPath={handleManualPath}
            showPathInput={showPathInput}
            pathInputValue={pathInputValue}
            pathInputRef={pathInputRef}
            onPathInputChange={setPathInputValue}
            onPathSubmit={handlePathSubmit}
            onPathInputCancel={() => setShowPathInput(false)}
          />
        )}

        {step === "llmSetup" && (
          <LLMSetupStep
            detectOllama={detectOllama}
            testLlmConnection={testLlmConnection}
            updateCategory={updateCategory}
            onContinue={() => {
              if (selectedPath) {
                handleParse(selectedPath);
              }
            }}
            onSkip={() => {
              updateCategory("llm", { enabled: false });
              if (selectedPath) {
                handleParse(selectedPath);
              }
            }}
          />
        )}

        {step === "scanning" && (
          <ScanningStep status={scanStatus} error={scanError} onRetry={handleRetry} />
        )}

        {step === "results" && parsedStats && (
          <ResultsStep
            path={selectedPath!}
            stats={parsedStats}
            edgeCount={parsedGraph.edges.length}
            onNext={() => setStep("explore")}
          />
        )}

        {step === "explore" && (
          <ExploreStep
            graph={parsedGraph}
            filters={defaultFilters}
            graphRef={graphRef}
            showTips={showTips}
            onDismissTips={() => setShowTips(false)}
            onFinish={handleFinish}
          />
        )}
      </div>

      {/* Step indicators */}
      <div className="flex items-center justify-center gap-2 py-4 border-t border-gray-800">
        {(["welcome", "llmSetup", "scanning", "results", "explore"] as WizardStep[]).map((s, i) => (
          <div
            key={s}
            className={`w-2 h-2 rounded-full transition-colors ${
              s === step ? "bg-blue-500" : i < ["welcome", "llmSetup", "scanning", "results", "explore"].indexOf(step) ? "bg-blue-800" : "bg-gray-700"
            }`}
          />
        ))}
      </div>
    </div>
  );
}

// --- Step Components ---

interface WelcomeStepProps {
  pyloidAvailable: boolean;
  onBrowse: () => void;
  onManualPath: () => void;
  showPathInput: boolean;
  pathInputValue: string;
  pathInputRef: React.RefObject<HTMLInputElement | null>;
  onPathInputChange: (value: string) => void;
  onPathSubmit: () => void;
  onPathInputCancel: () => void;
}

function WelcomeStep({
  pyloidAvailable,
  onBrowse,
  onManualPath,
  showPathInput,
  pathInputValue,
  pathInputRef,
  onPathInputChange,
  onPathSubmit,
  onPathInputCancel,
}: WelcomeStepProps) {
  return (
    <div className="text-center max-w-lg px-8">
      <div className="w-20 h-20 bg-blue-600/20 rounded-2xl flex items-center justify-center mx-auto mb-8">
        <svg className="w-10 h-10 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      </div>

      <h2 className="text-3xl font-bold text-gray-100 mb-3">Welcome to Docmaker</h2>
      <p className="text-gray-400 mb-8 leading-relaxed">
        Visualize your codebase as an interactive graph. Select a project folder to get started.
      </p>

      <div className="flex flex-col gap-3 items-center">
        <button
          onClick={onBrowse}
          className="w-72 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center justify-center gap-3 transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
          </svg>
          Select Project Folder
        </button>

        {!showPathInput ? (
          <button
            onClick={onManualPath}
            className="w-72 px-6 py-3 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg flex items-center justify-center gap-3 border border-gray-700 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
            </svg>
            Enter Path Manually
          </button>
        ) : (
          <div className="w-72">
            <input
              ref={pathInputRef}
              type="text"
              value={pathInputValue}
              onChange={(e) => onPathInputChange(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") onPathSubmit();
                if (e.key === "Escape") onPathInputCancel();
              }}
              placeholder="/path/to/project"
              className="w-full px-4 py-3 bg-gray-800 border border-gray-600 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-blue-500 mb-2"
            />
            <div className="flex gap-2">
              <button
                onClick={onPathInputCancel}
                className="flex-1 px-3 py-2 text-sm text-gray-400 hover:text-gray-200 rounded"
              >
                Cancel
              </button>
              <button
                onClick={onPathSubmit}
                className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded"
              >
                Open
              </button>
            </div>
          </div>
        )}
      </div>

      {!pyloidAvailable && (
        <p className="text-xs text-yellow-500/70 mt-6">
          Running in dev mode — native folder picker may not be available
        </p>
      )}
    </div>
  );
}

interface ScanningStepProps {
  status: string;
  error: string | null;
  onRetry: () => void;
}

function ScanningStep({ status, error, onRetry }: ScanningStepProps) {
  return (
    <div className="text-center max-w-md px-8">
      {error ? (
        <>
          <div className="w-16 h-16 bg-red-600/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-100 mb-2">Something went wrong</h3>
          <p className="text-sm text-red-400 mb-6 font-mono bg-red-950/30 rounded-lg px-4 py-3">{error}</p>
          <button
            onClick={onRetry}
            className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
          >
            Try Again
          </button>
        </>
      ) : (
        <>
          <div className="w-16 h-16 bg-blue-600/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
            <svg className="w-8 h-8 text-blue-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          </div>
          <h3 className="text-xl font-semibold text-gray-100 mb-2">Analyzing your project</h3>
          <p className="text-gray-400">{status}</p>
        </>
      )}
    </div>
  );
}

interface ResultsStepProps {
  path: string;
  stats: { files: number; classes: number; endpoints: number };
  edgeCount: number;
  onNext: () => void;
}

function ResultsStep({ path, stats, edgeCount, onNext }: ResultsStepProps) {
  const folderName = path.split(/[\\/]/).pop() || path;

  return (
    <div className="text-center max-w-lg px-8">
      <div className="w-16 h-16 bg-green-600/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
        <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      </div>

      <h3 className="text-2xl font-bold text-gray-100 mb-2">Project analyzed</h3>
      <p className="text-gray-400 mb-8">
        <span className="text-gray-200 font-medium">{folderName}</span> has been parsed successfully.
      </p>

      <div className="grid grid-cols-2 gap-4 mb-8">
        <StatCard label="Files parsed" value={stats.files} icon="file" />
        <StatCard label="Classes found" value={stats.classes} icon="class" />
        <StatCard label="Endpoints" value={stats.endpoints} icon="endpoint" />
        <StatCard label="Graph connections" value={edgeCount} icon="edge" />
      </div>

      <button
        onClick={onNext}
        className="px-8 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2 mx-auto"
      >
        View Graph
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
        </svg>
      </button>
    </div>
  );
}

function StatCard({ label, value, icon }: { label: string; value: number; icon: string }) {
  const iconColors: Record<string, string> = {
    file: "text-blue-400",
    class: "text-purple-400",
    endpoint: "text-green-400",
    edge: "text-yellow-400",
  };

  const icons: Record<string, React.ReactNode> = {
    file: (
      <svg className={`w-5 h-5 ${iconColors[icon]}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z" />
      </svg>
    ),
    class: (
      <svg className={`w-5 h-5 ${iconColors[icon]}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
      </svg>
    ),
    endpoint: (
      <svg className={`w-5 h-5 ${iconColors[icon]}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
      </svg>
    ),
    edge: (
      <svg className={`w-5 h-5 ${iconColors[icon]}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
      </svg>
    ),
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4 text-left">
      <div className="flex items-center gap-2 mb-1">
        {icons[icon]}
        <span className="text-sm text-gray-400">{label}</span>
      </div>
      <span className="text-2xl font-bold text-gray-100">{value.toLocaleString()}</span>
    </div>
  );
}

interface LLMSetupStepProps {
  detectOllama: (baseUrl: string) => Promise<{ available: boolean; models: string[] }>;
  testLlmConnection: (config: import("../types/settings").LLMSettings) => Promise<{ success: boolean; error?: string }>;
  updateCategory: <K extends keyof import("../types/settings").AppSettings>(
    category: K,
    values: Partial<import("../types/settings").AppSettings[K]>
  ) => void;
  onContinue: () => void;
  onSkip: () => void;
}

function LLMSetupStep({ detectOllama, testLlmConnection, updateCategory, onContinue, onSkip }: LLMSetupStepProps) {
  const [provider, setProvider] = useState<LLMProvider>("ollama");
  const [model, setModel] = useState(DEFAULT_SETTINGS.llm.model);
  const [baseUrl, setBaseUrl] = useState(DEFAULT_SETTINGS.llm.baseUrl);
  const [apiKey, setApiKey] = useState("");
  const [detectedModels, setDetectedModels] = useState<string[]>([]);
  const [ollamaStatus, setOllamaStatus] = useState<"checking" | "found" | "not_found">("checking");
  const [testStatus, setTestStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [testError, setTestError] = useState<string | null>(null);

  // Auto-detect Ollama on mount
  useEffect(() => {
    let cancelled = false;
    detectOllama(DEFAULT_SETTINGS.llm.baseUrl).then((result) => {
      if (cancelled) return;
      if (result.available) {
        setOllamaStatus("found");
        setDetectedModels(result.models);
        if (result.models.length > 0) {
          setModel(result.models[0]);
        }
      } else {
        setOllamaStatus("not_found");
      }
    });
    return () => { cancelled = true; };
  }, [detectOllama]);

  const handleTest = useCallback(async () => {
    setTestStatus("testing");
    setTestError(null);
    const result = await testLlmConnection({
      enabled: true,
      provider,
      model,
      baseUrl,
      apiKey,
      timeout: DEFAULT_SETTINGS.llm.timeout,
    });
    if (result.success) {
      setTestStatus("success");
    } else {
      setTestStatus("error");
      setTestError(result.error || "Connection failed");
    }
  }, [provider, model, baseUrl, apiKey, testLlmConnection]);

  const handleContinue = useCallback(() => {
    updateCategory("llm", {
      enabled: true,
      provider,
      model,
      baseUrl,
      apiKey,
      timeout: DEFAULT_SETTINGS.llm.timeout,
    });
    onContinue();
  }, [provider, model, baseUrl, apiKey, updateCategory, onContinue]);

  const needsUrl = provider === "ollama" || provider === "lmstudio";
  const needsKey = provider === "openai" || provider === "anthropic";

  return (
    <div className="text-center max-w-lg px-8">
      <div className="w-16 h-16 bg-purple-600/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
        <svg className="w-8 h-8 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.75 3.104v5.714a2.25 2.25 0 01-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 014.5 0m0 0v5.714a2.25 2.25 0 00.659 1.591L19 14.5M14.25 3.104c.251.023.501.05.75.082M19 14.5l-2.47 2.47a2.25 2.25 0 01-1.59.659H9.06a2.25 2.25 0 01-1.591-.659L5 14.5m14 0V17a2.25 2.25 0 01-2.25 2.25H7.25A2.25 2.25 0 015 17v-2.5" />
        </svg>
      </div>

      <h3 className="text-2xl font-bold text-gray-100 mb-2">LLM Classification</h3>
      <p className="text-gray-400 mb-6 leading-relaxed">
        Docmaker can use an LLM to intelligently classify your source files. This is optional but improves accuracy.
      </p>

      {/* Ollama auto-detect status */}
      {ollamaStatus === "checking" && (
        <div className="flex items-center justify-center gap-2 text-sm text-gray-400 mb-6">
          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          Checking for Ollama...
        </div>
      )}

      {ollamaStatus === "found" && (
        <div className="flex items-center justify-center gap-2 text-sm text-green-400 mb-6 bg-green-950/30 rounded-lg px-4 py-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
          Ollama detected — {detectedModels.length} model{detectedModels.length !== 1 ? "s" : ""} available
        </div>
      )}

      {ollamaStatus === "not_found" && (
        <div className="text-sm text-gray-500 mb-6 bg-gray-800/50 rounded-lg px-4 py-2">
          Ollama not detected at default URL. You can configure a different provider or skip this step.
        </div>
      )}

      {/* Provider selector */}
      <div className="text-left space-y-4 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1.5">Provider</label>
          <select
            value={provider}
            onChange={(e) => {
              setProvider(e.target.value as LLMProvider);
              setTestStatus("idle");
            }}
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          >
            {(["ollama", "lmstudio", "openai", "anthropic"] as LLMProvider[]).map((p) => (
              <option key={p} value={p}>{LLM_PROVIDER_LABELS[p]}</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-300 mb-1.5">Model</label>
          <input
            type="text"
            value={model}
            onChange={(e) => { setModel(e.target.value); setTestStatus("idle"); }}
            placeholder="llama3.2"
            className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-blue-500"
          />
          {detectedModels.length > 0 && provider === "ollama" && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {detectedModels.map((m) => (
                <button
                  key={m}
                  onClick={() => { setModel(m); setTestStatus("idle"); }}
                  className={`px-2 py-1 text-xs rounded border transition-colors ${
                    m === model
                      ? "bg-blue-600/20 border-blue-500 text-blue-400"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200 hover:border-gray-600"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          )}
        </div>

        {needsUrl && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">Base URL</label>
            <input
              type="text"
              value={baseUrl}
              onChange={(e) => { setBaseUrl(e.target.value); setTestStatus("idle"); }}
              placeholder="http://localhost:11434"
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            />
          </div>
        )}

        {needsKey && (
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-1.5">API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => { setApiKey(e.target.value); setTestStatus("idle"); }}
              placeholder="sk-..."
              className="w-full px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm text-gray-100 focus:outline-none focus:border-blue-500"
            />
          </div>
        )}

        {/* Test Connection */}
        <div className="flex items-center gap-3">
          <button
            onClick={handleTest}
            disabled={testStatus === "testing"}
            className="px-4 py-2 text-sm bg-gray-800 border border-gray-700 rounded-lg text-gray-300 hover:text-white hover:border-gray-600 transition-colors disabled:opacity-50"
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
            <span className="text-sm text-red-400">{testError}</span>
          )}
        </div>
      </div>

      {/* Actions */}
      <div className="flex flex-col gap-3 items-center">
        <button
          onClick={handleContinue}
          className="w-72 px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white rounded-lg flex items-center justify-center gap-2 transition-colors"
        >
          Continue
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
        <button
          onClick={onSkip}
          className="text-sm text-gray-500 hover:text-gray-300 transition-colors"
        >
          Skip — scan without LLM
        </button>
      </div>
    </div>
  );
}

interface ExploreStepProps {
  graph: CodeGraph;
  filters: FilterState;
  graphRef: React.RefObject<GraphViewHandle | null>;
  showTips: boolean;
  onDismissTips: () => void;
  onFinish: () => void;
}

function ExploreStep({ graph, filters, graphRef, showTips, onDismissTips, onFinish }: ExploreStepProps) {
  return (
    <div className="w-full h-full flex flex-col relative">
      {/* Graph takes full space */}
      <div className="flex-1 relative">
        <GraphView
          ref={graphRef}
          graph={graph}
          filters={filters}
          selectedNodeId={null}
          onNodeSelect={() => {}}
          onNodeDoubleClick={() => {}}
          onEdgeTypeToggle={() => {}}
        />

        {/* Tips overlay */}
        {showTips && (
          <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
            <div className="bg-gray-800 border border-gray-700 rounded-xl p-6 max-w-md shadow-2xl">
              <h3 className="text-lg font-semibold text-gray-100 mb-4">Your Code Graph</h3>
              <ul className="space-y-3 text-sm text-gray-300 mb-6">
                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 bg-blue-600/30 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-xs text-blue-400 font-bold">1</span>
                  <span><b className="text-gray-100">Click a node</b> to see its details — classes, methods, fields, and connections.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 bg-blue-600/30 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-xs text-blue-400 font-bold">2</span>
                  <span><b className="text-gray-100">Double-click</b> to open a file directly in your editor.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 bg-blue-600/30 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-xs text-blue-400 font-bold">3</span>
                  <span>Use the <b className="text-gray-100">sidebar filters</b> to focus on specific node types or categories.</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="w-6 h-6 bg-blue-600/30 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 text-xs text-blue-400 font-bold">4</span>
                  <span>Press <kbd className="px-1.5 py-0.5 bg-gray-700 border border-gray-600 rounded text-xs">?</kbd> anytime to see all keyboard shortcuts.</span>
                </li>
              </ul>
              <button
                onClick={onDismissTips}
                className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors"
              >
                Got it
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Bottom action bar */}
      <div className="flex items-center justify-between px-6 py-4 bg-gray-800/80 border-t border-gray-700">
        <p className="text-sm text-gray-400">
          {graph.nodes.length} nodes, {graph.edges.length} connections
        </p>
        <button
          onClick={onFinish}
          className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors flex items-center gap-2"
        >
          Start Exploring
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7l5 5m0 0l-5 5m5-5H6" />
          </svg>
        </button>
      </div>
    </div>
  );
}
