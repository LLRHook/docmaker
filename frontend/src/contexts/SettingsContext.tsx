import {
  createContext,
  useContext,
  useState,
  useCallback,
  useEffect,
  useRef,
  type ReactNode,
} from "react";
import { ipc, pyloidReadyManager } from "pyloid-js";
import type { AppSettings } from "../types/settings";
import { DEFAULT_SETTINGS } from "../types/settings";
import { createLogger } from "../utils/logger";

const logger = createLogger("SettingsContext");

const STORAGE_KEY = "docmaker-settings";

interface SettingsContextValue {
  settings: AppSettings;
  updateSettings: (newSettings: Partial<AppSettings>) => void;
  updateCategory: <K extends keyof AppSettings>(
    category: K,
    values: Partial<AppSettings[K]>
  ) => void;
  resetSettings: () => Promise<void>;
  isLoading: boolean;
}

const SettingsContext = createContext<SettingsContextValue | null>(null);

function loadFromLocalStorage(): AppSettings {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored) as Partial<AppSettings>;
      return deepMerge(DEFAULT_SETTINGS, parsed);
    }
  } catch (e) {
    logger.warn("Failed to load settings from localStorage:", e);
  }
  return { ...DEFAULT_SETTINGS };
}

function saveToLocalStorage(settings: AppSettings): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));
  } catch (e) {
    logger.warn("Failed to save settings to localStorage:", e);
  }
}

function deepMerge(base: AppSettings, override: Partial<AppSettings>): AppSettings {
  const result: AppSettings = {
    graphView: { ...base.graphView, ...override.graphView },
    appearance: { ...base.appearance, ...override.appearance },
    editor: { ...base.editor, ...override.editor },
    general: { ...base.general, ...override.general },
    layout: { ...base.layout, ...override.layout },
  };
  return result;
}

interface SettingsProviderProps {
  children: ReactNode;
}

export function SettingsProvider({ children }: SettingsProviderProps) {
  const [settings, setSettings] = useState<AppSettings>(loadFromLocalStorage);
  const [isLoading, setIsLoading] = useState(true);
  const saveTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load settings from backend on mount
  useEffect(() => {
    let cancelled = false;

    const loadFromBackend = async () => {
      if (!pyloidReadyManager.isReady()) {
        logger.debug("Pyloid not ready, using localStorage settings");
        setIsLoading(false);
        return;
      }

      try {
        const result = await ipc.DocmakerAPI.get_settings();
        const parsed = JSON.parse(result) as Partial<AppSettings> & { error?: string };

        if (!cancelled && !parsed.error) {
          const merged = deepMerge(DEFAULT_SETTINGS, parsed);
          setSettings(merged);
          saveToLocalStorage(merged);
          logger.info("Settings loaded from backend");
        }
      } catch (e) {
        logger.warn("Failed to load settings from backend:", e);
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    // Wait for Pyloid to be ready, then load
    pyloidReadyManager
      .whenReady()
      .then(loadFromBackend)
      .catch(() => {
        if (!cancelled) {
          setIsLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, []);

  // Debounced save to backend
  const saveToBackend = useCallback((newSettings: AppSettings) => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }

    saveTimeoutRef.current = setTimeout(async () => {
      if (!pyloidReadyManager.isReady()) {
        return;
      }

      try {
        await ipc.DocmakerAPI.save_settings_ipc(JSON.stringify(newSettings));
        logger.debug("Settings saved to backend");
      } catch (e) {
        logger.warn("Failed to save settings to backend:", e);
      }
    }, 500);
  }, []);

  const updateSettings = useCallback(
    (newSettings: Partial<AppSettings>) => {
      setSettings((prev) => {
        const updated: AppSettings = {
          graphView: { ...prev.graphView, ...newSettings.graphView },
          appearance: { ...prev.appearance, ...newSettings.appearance },
          editor: { ...prev.editor, ...newSettings.editor },
          general: { ...prev.general, ...newSettings.general },
          layout: { ...prev.layout, ...newSettings.layout },
        };
        saveToLocalStorage(updated);
        saveToBackend(updated);
        return updated;
      });
    },
    [saveToBackend]
  );

  const updateCategory = useCallback(
    <K extends keyof AppSettings>(category: K, values: Partial<AppSettings[K]>) => {
      setSettings((prev) => {
        const updated = {
          ...prev,
          [category]: { ...prev[category], ...values },
        };
        saveToLocalStorage(updated);
        saveToBackend(updated);
        return updated;
      });
    },
    [saveToBackend]
  );

  const resetSettings = useCallback(async () => {
    if (pyloidReadyManager.isReady()) {
      try {
        const result = await ipc.DocmakerAPI.reset_settings_ipc();
        const parsed = JSON.parse(result) as AppSettings & { error?: string };
        if (!parsed.error) {
          const validSettings: AppSettings = {
            graphView: parsed.graphView,
            appearance: parsed.appearance,
            editor: parsed.editor,
            general: parsed.general,
            layout: parsed.layout || DEFAULT_SETTINGS.layout,
          };
          setSettings(validSettings);
          saveToLocalStorage(validSettings);
          logger.info("Settings reset to defaults");
          return;
        }
      } catch (e) {
        logger.warn("Failed to reset settings via backend:", e);
      }
    }

    // Fallback: reset locally
    setSettings({ ...DEFAULT_SETTINGS });
    saveToLocalStorage(DEFAULT_SETTINGS);
    logger.info("Settings reset to defaults (local)");
  }, []);

  // Cleanup timeout on unmount
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  return (
    <SettingsContext.Provider
      value={{ settings, updateSettings, updateCategory, resetSettings, isLoading }}
    >
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings(): SettingsContextValue {
  const context = useContext(SettingsContext);
  if (!context) {
    throw new Error("useSettings must be used within a SettingsProvider");
  }
  return context;
}
