export interface GraphViewSettings {
  scrollSpeed: number;
  zoomSensitivity: number;
  animationSpeed: "none" | "fast" | "normal" | "slow";
  defaultLayout: "cose" | "circle" | "grid";
  showLabels: boolean;
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

export interface GeneralSettings {
  openLastProjectOnStartup: boolean;
  lastProjectPath: string | null;
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
    defaultLayout: "cose",
    showLabels: true,
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
