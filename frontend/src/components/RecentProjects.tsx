import type { RecentProject } from "../types/settings";

interface RecentProjectsProps {
  recentProjects: RecentProject[];
  onOpenProject: (path: string) => void;
  onRemoveProject: (path: string) => void;
  onBrowse: () => void;
}

function formatRelativeTime(isoDate: string): string {
  const date = new Date(isoDate);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}

export function RecentProjects({
  recentProjects,
  onOpenProject,
  onRemoveProject,
  onBrowse,
}: RecentProjectsProps) {
  return (
    <div className="flex items-center justify-center h-full">
      <div className="w-full max-w-md px-6">
        <div className="text-center mb-8">
          <svg
            className="w-12 h-12 mx-auto mb-3 text-blue-500 opacity-80"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M13 10V3L4 14h7v7l9-11h-7z"
            />
          </svg>
          <h2 className="text-xl font-semibold text-gray-200">Docmaker</h2>
          <p className="text-sm text-gray-500 mt-1">
            Open a project to visualize its architecture
          </p>
        </div>

        {recentProjects.length > 0 && (
          <div className="mb-6">
            <h3 className="text-xs font-medium text-gray-400 uppercase tracking-wider mb-2">
              Recent Projects
            </h3>
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg overflow-hidden">
              {recentProjects.map((project, index) => (
                <button
                  key={project.path}
                  onClick={() => onOpenProject(project.path)}
                  className={`w-full px-4 py-3 text-left hover:bg-gray-700/50 flex items-center gap-3 group ${
                    index > 0 ? "border-t border-gray-700/30" : ""
                  }`}
                >
                  <svg
                    className="w-5 h-5 text-gray-500 shrink-0"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                    />
                  </svg>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-gray-200 truncate">
                      {project.name}
                    </p>
                    <p className="text-xs text-gray-500 truncate font-mono">
                      {project.path}
                    </p>
                  </div>
                  <span className="text-xs text-gray-600 shrink-0">
                    {formatRelativeTime(project.lastOpened)}
                  </span>
                  <span
                    onClick={(e) => {
                      e.stopPropagation();
                      onRemoveProject(project.path);
                    }}
                    className="text-gray-600 hover:text-gray-400 opacity-0 group-hover:opacity-100 p-1 shrink-0"
                    title="Remove from recent"
                  >
                    <svg
                      className="w-3.5 h-3.5"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        <button
          onClick={onBrowse}
          className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white text-sm rounded-lg flex items-center justify-center gap-2"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
            />
          </svg>
          Open Project
        </button>
      </div>
    </div>
  );
}
