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

export interface AppSettings {
  graphView: GraphViewSettings;
  appearance: AppearanceSettings;
  editor: EditorSettings;
  general: GeneralSettings;
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
};

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
