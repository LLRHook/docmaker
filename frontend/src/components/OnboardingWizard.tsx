import { useState, useCallback } from "react";

interface OnboardingWizardProps {
  onSelectFolder: () => Promise<void>;
  onComplete: () => void;
  /** Set externally when project loads successfully */
  projectLoaded: boolean;
  loadStats: { files: number; classes: number; endpoints: number } | null;
  loadStatus: "idle" | "scanning" | "parsing" | "ready" | "error";
  loadMessage: string;
}

type WizardStep = "welcome" | "loading" | "results" | "tips";

export function OnboardingWizard({
  onSelectFolder,
  onComplete,
  projectLoaded,
  loadStats,
  loadStatus,
  loadMessage,
}: OnboardingWizardProps) {
  const [step, setStep] = useState<WizardStep>("welcome");

  const handleOpenProject = useCallback(async () => {
    setStep("loading");
    await onSelectFolder();
  }, [onSelectFolder]);

  // Auto-advance from loading to results when project is loaded
  if (step === "loading" && projectLoaded && loadStatus === "ready") {
    setStep("results");
  }

  // Handle error during loading - allow retry
  if (step === "loading" && loadStatus === "error") {
    // Stay on loading step but show error
  }

  return (
    <div className="fixed inset-0 z-50 bg-gray-900/95 flex items-center justify-center">
      <div className="w-full max-w-lg mx-4">
        {/* Progress dots */}
        <div className="flex justify-center gap-2 mb-8">
          {(["welcome", "loading", "results", "tips"] as const).map((s, i) => {
            const steps: WizardStep[] = ["welcome", "loading", "results", "tips"];
            const currentIndex = steps.indexOf(step);
            const isActive = i === currentIndex;
            const isDone = i < currentIndex;
            return (
              <div
                key={s}
                className={`w-2.5 h-2.5 rounded-full transition-colors ${
                  isActive
                    ? "bg-blue-500"
                    : isDone
                      ? "bg-blue-400/60"
                      : "bg-gray-700"
                }`}
              />
            );
          })}
        </div>

        {/* Step content */}
        {step === "welcome" && (
          <div className="text-center">
            <div className="w-20 h-20 mx-auto mb-6 bg-blue-600/20 rounded-2xl flex items-center justify-center">
              <svg className="w-10 h-10 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h2 className="text-2xl font-semibold text-gray-100 mb-3">Welcome to Docmaker</h2>
            <p className="text-gray-400 mb-8 max-w-sm mx-auto">
              Generate interactive documentation and knowledge graphs from your codebase. Let's start by opening a project.
            </p>
            <button
              onClick={handleOpenProject}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-sm inline-flex items-center gap-2 text-sm"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z" />
              </svg>
              Choose a Project Folder
            </button>
            <p className="text-xs text-gray-600 mt-4">
              Or drag and drop a folder anywhere on this window
            </p>
          </div>
        )}

        {step === "loading" && (
          <div className="text-center">
            {loadStatus === "error" ? (
              <>
                <div className="w-16 h-16 mx-auto mb-4 bg-red-600/20 rounded-2xl flex items-center justify-center">
                  <svg className="w-8 h-8 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                  </svg>
                </div>
                <h2 className="text-xl font-semibold text-gray-100 mb-2">Something went wrong</h2>
                <p className="text-sm text-red-400 mb-6">{loadMessage}</p>
                <div className="flex gap-3 justify-center">
                  <button
                    onClick={() => setStep("welcome")}
                    className="px-4 py-2 text-sm text-gray-400 hover:text-gray-200"
                  >
                    Go Back
                  </button>
                  <button
                    onClick={handleOpenProject}
                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-sm"
                  >
                    Try Again
                  </button>
                </div>
              </>
            ) : (
              <>
                <svg className="w-10 h-10 mx-auto mb-4 text-blue-500 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                <h2 className="text-xl font-semibold text-gray-100 mb-2">
                  {loadStatus === "scanning" ? "Scanning files..." : "Parsing source code..."}
                </h2>
                <p className="text-sm text-gray-500">{loadMessage}</p>
              </>
            )}
          </div>
        )}

        {step === "results" && loadStats && (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-600/20 rounded-2xl flex items-center justify-center">
              <svg className="w-8 h-8 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold text-gray-100 mb-2">Project parsed successfully</h2>
            <p className="text-sm text-gray-400 mb-6">Here's what we found in your codebase:</p>

            <div className="grid grid-cols-3 gap-4 mb-8">
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-400">{loadStats.files}</div>
                <div className="text-xs text-gray-500 mt-1">Files</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-purple-400">{loadStats.classes}</div>
                <div className="text-xs text-gray-500 mt-1">Classes</div>
              </div>
              <div className="bg-gray-800 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-400">{loadStats.endpoints}</div>
                <div className="text-xs text-gray-500 mt-1">Endpoints</div>
              </div>
            </div>

            <button
              onClick={() => setStep("tips")}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-sm"
            >
              Continue
            </button>
          </div>
        )}

        {step === "tips" && (
          <div className="text-center">
            <h2 className="text-xl font-semibold text-gray-100 mb-6">Quick tips</h2>

            <div className="space-y-4 text-left mb-8">
              <div className="flex gap-3 items-start">
                <div className="w-8 h-8 bg-gray-800 rounded flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-200">Click nodes</div>
                  <div className="text-xs text-gray-500">Select any node in the graph to view its details</div>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <div className="w-8 h-8 bg-gray-800 rounded flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-200">Double-click to open</div>
                  <div className="text-xs text-gray-500">Double-click a node to open the source file in your editor</div>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <div className="w-8 h-8 bg-gray-800 rounded flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-200">Search and filter</div>
                  <div className="text-xs text-gray-500">Use the sidebar to search nodes and filter by type. Press <kbd className="px-1 bg-gray-700 rounded text-xs">/</kbd> to focus search.</div>
                </div>
              </div>
              <div className="flex gap-3 items-start">
                <div className="w-8 h-8 bg-gray-800 rounded flex items-center justify-center shrink-0">
                  <svg className="w-4 h-4 text-yellow-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                  </svg>
                </div>
                <div>
                  <div className="text-sm font-medium text-gray-200">Press <kbd className="px-1 bg-gray-700 rounded text-xs">?</kbd> for keyboard shortcuts</div>
                  <div className="text-xs text-gray-500">Navigate the graph, toggle filters, and more with keyboard</div>
                </div>
              </div>
            </div>

            <button
              onClick={onComplete}
              className="px-6 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-sm"
            >
              Get Started
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
