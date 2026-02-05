interface StatusBarProps {
  projectPath: string | null;
  stats: {
    files: number;
    classes: number;
    endpoints: number;
  } | null;
  status: "idle" | "scanning" | "parsing" | "generating" | "ready" | "error";
  message?: string;
}

export function StatusBar({ projectPath, stats, status, message }: StatusBarProps) {
  const statusColors = {
    idle: "bg-gray-600",
    scanning: "bg-yellow-600",
    parsing: "bg-blue-600",
    generating: "bg-purple-600",
    ready: "bg-green-600",
    error: "bg-red-600",
  };

  const statusLabels = {
    idle: "Ready",
    scanning: "Scanning...",
    parsing: "Parsing...",
    generating: "Generating...",
    ready: "Ready",
    error: "Error",
  };

  return (
    <div className="h-8 bg-gray-800 border-t border-gray-700 flex items-center px-4 text-sm">
      <div className="flex items-center gap-2">
        <span
          className={`w-2 h-2 rounded-full ${statusColors[status]} ${
            status === "scanning" || status === "parsing" || status === "generating"
              ? "animate-pulse"
              : ""
          }`}
        />
        <span className="text-gray-400">{message || statusLabels[status]}</span>
      </div>

      <div className="flex-1" />

      {projectPath && (
        <div className="flex items-center gap-4 text-gray-400">
          <span className="truncate max-w-xs" title={projectPath}>
            {projectPath}
          </span>
          {stats && (
            <>
              <span className="text-gray-600">|</span>
              <span>{stats.files} files</span>
              <span>{stats.classes} classes</span>
              <span>{stats.endpoints} endpoints</span>
            </>
          )}
        </div>
      )}
    </div>
  );
}
