export type EdgeType = "extends" | "implements" | "imports" | "calls" | "contains";

export const ALL_EDGE_TYPES: EdgeType[] = ["extends", "implements", "imports", "calls", "contains"];

export interface EdgeTypeFilters {
  extends: boolean;
  implements: boolean;
  imports: boolean;
  calls: boolean;
  contains: boolean;
}

export interface GraphViewSettings {
  scrollSpeed: number;
  zoomSensitivity: number;
  animationSpeed: "none" | "fast" | "normal" | "slow";
  defaultLayout: "fcose" | "cose" | "circle" | "grid";
  showLabels: boolean;
  layoutQuality: "draft" | "default" | "proof";
  nodeSizing: "fixed" | "byType" | "byDegree";
  largeGraphThreshold: number;
  edgeTypeFilters: Record<EdgeType, boolean>;
  enablePackageClustering: boolean;
}

export interface AppearanceSettings {
  fontSize: "small" | "medium" | "large";
  uiScale: number;
}

export interface EditorSettings {
  preferredEditor: "auto" | "vscode" | "idea" | "sublime" | "system" | "custom";
  customEditorCommand: string;
  alwaysAsk: boolean;
}

export interface RecentProject {
  path: string;
  name: string;
  lastOpened: string; // ISO 8601 timestamp
}

export interface GeneralSettings {
  openLastProjectOnStartup: boolean;
  lastProjectPath: string | null;
  recentProjects: RecentProject[];
  firstRunCompleted: boolean;
}

export interface LayoutSettings {
  windowWidth: number;
  windowHeight: number;
  sidebarWidth: number;
  detailsPanelWidth: number;
}

export interface AppSettings {
  graphView: GraphViewSettings;
  appearance: AppearanceSettings;
  editor: EditorSettings;
  general: GeneralSettings;
  layout: LayoutSettings;
}

export const DEFAULT_SETTINGS: AppSettings = {
  graphView: {
    scrollSpeed: 0.3,
    zoomSensitivity: 0.2,
    animationSpeed: "normal",
    defaultLayout: "fcose",
    showLabels: true,
    layoutQuality: "default",
    nodeSizing: "byDegree",
    largeGraphThreshold: 200,
    edgeTypeFilters: {
      extends: true,
      implements: true,
      imports: true,
      calls: true,
      contains: true,
    },
    enablePackageClustering: false,
  },
  appearance: {
    fontSize: "medium",
    uiScale: 100,
  },
  editor: {
    preferredEditor: "auto",
    customEditorCommand: "",
    alwaysAsk: false,
  },
  general: {
    openLastProjectOnStartup: false,
    lastProjectPath: null,
    recentProjects: [],
    firstRunCompleted: false,
  },
  layout: {
    windowWidth: 1280,
    windowHeight: 720,
    sidebarWidth: 288,
    detailsPanelWidth: 320,
  },
};

export const WINDOW_PRESETS: { label: string; width: number; height: number }[] = [
  { label: "1280×720 (HD)", width: 1280, height: 720 },
  { label: "1366×768", width: 1366, height: 768 },
  { label: "1920×1080 (Full HD)", width: 1920, height: 1080 },
  { label: "2560×1440 (QHD)", width: 2560, height: 1440 },
];

export const MIN_SIDEBAR_WIDTH = 150;
export const MIN_DETAILS_PANEL_WIDTH = 150;
export const MAX_SIDEBAR_WIDTH = 500;
export const MAX_DETAILS_PANEL_WIDTH = 600;

export const FONT_SIZE_VALUES: Record<AppearanceSettings["fontSize"], number> = {
  small: 12,
  medium: 14,
  large: 16,
};

export const ANIMATION_DURATION: Record<GraphViewSettings["animationSpeed"], number> = {
  none: 0,
  fast: 150,
  normal: 300,
  slow: 500,
};

export const EDITOR_LABELS: Record<EditorSettings["preferredEditor"], string> = {
  auto: "Auto-detect (VS Code → system)",
  vscode: "Visual Studio Code",
  idea: "IntelliJ IDEA",
  sublime: "Sublime Text",
  system: "System Default",
  custom: "Custom Command",
};

export const FONT_SIZE_LABELS: Record<AppearanceSettings["fontSize"], string> = {
  small: "Small",
  medium: "Medium",
  large: "Large",
};

export const LAYOUT_LABELS: Record<GraphViewSettings["defaultLayout"], string> = {
  fcose: "Force-directed (fCoSE - recommended)",
  cose: "Force-directed (CoSE)",
  circle: "Circular",
  grid: "Grid",
};

export const LAYOUT_QUALITY_LABELS: Record<GraphViewSettings["layoutQuality"], string> = {
  draft: "Draft (fastest)",
  default: "Balanced",
  proof: "High Quality (slowest)",
};

export const NODE_SIZING_LABELS: Record<GraphViewSettings["nodeSizing"], string> = {
  fixed: "Fixed Size",
  byType: "By Node Type",
  byDegree: "By Connection Count",
};

export const EDGE_TYPE_LABELS: Record<keyof EdgeTypeFilters, string> = {
  extends: "Extends",
  implements: "Implements",
  imports: "Imports",
  calls: "Calls",
  contains: "Contains",
};

export const EDGE_TYPE_COLORS: Record<keyof EdgeTypeFilters, string> = {
  extends: "#3b82f6",
  implements: "#a855f7",
  imports: "#6b7280",
  calls: "#f59e0b",
  contains: "#4b5563",
};
