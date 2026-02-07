import { useCallback, useRef, useState, useEffect } from "react";
import { ipc, pyloidReadyManager } from "pyloid-js";
import type {
  ScanResult,
  GenerateResult,
  ParseResult,
  ProjectInfo,
  ClassDetails,
  EndpointDetails,
  CodeGraph,
  SourceSnippet,
} from "../types/graph";
import { createLogger } from "../utils/logger";
import { markStart, markEnd } from "../utils/perf";

const logger = createLogger("usePyloid");

interface GenerateOptions {
  incremental?: boolean;
  useLlm?: boolean;
}

export function usePyloid() {
  const [ready, setReady] = useState(() => pyloidReadyManager.isReady());
  const classDetailsCache = useRef(new Map<string, ClassDetails>());
  const endpointDetailsCache = useRef(new Map<string, EndpointDetails>());

  // Wait for Pyloid to be ready (polls for window.__PYLOID__)
  useEffect(() => {
    if (ready) {
      logger.info("Pyloid API already available");
      return;
    }

    let cancelled = false;

    pyloidReadyManager.whenReady()
      .then(() => {
        if (!cancelled) {
          logger.info("Pyloid API is now ready");
          setReady(true);
        }
      })
      .catch((error) => {
        if (!cancelled) {
          logger.error("Pyloid initialization failed:", error);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [ready]);

  const isAvailable = useCallback(() => {
    return pyloidReadyManager.isReady();
  }, []);

  const selectFolder = useCallback(async (): Promise<string | null> => {
    logger.debug("selectFolder called");
    try {
      const result = await ipc.DocmakerAPI.select_folder();
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("Error selecting folder:", parsed.error);
        return null;
      }
      logger.info("Folder selected:", parsed.path);
      return parsed.path;
    } catch (error) {
      logger.error("selectFolder failed:", error);
      return null;
    }
  }, []);

  const scanProject = useCallback(async (path: string): Promise<ScanResult> => {
    logger.info("scanProject called with path:", path);
    try {
      const result = await ipc.DocmakerAPI.scan_project(path);
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("scanProject error:", parsed.error);
      } else {
        logger.info("scanProject success:", parsed.stats);
      }
      return parsed;
    } catch (error) {
      logger.error("scanProject failed:", error);
      return {
        projectPath: "",
        files: [],
        stats: { totalFiles: 0, byLanguage: {}, byCategory: {} },
        error: String(error)
      };
    }
  }, []);

  const generateDocs = useCallback(async (options: GenerateOptions = {}): Promise<GenerateResult> => {
    logger.info("generateDocs called with options:", options);
    try {
      const result = await ipc.DocmakerAPI.generate_docs(JSON.stringify(options));
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("generateDocs error:", parsed.error);
      } else {
        logger.info("generateDocs success:", parsed.stats);
      }
      return parsed;
    } catch (error) {
      logger.error("generateDocs failed:", error);
      return {
        success: false,
        generatedFiles: [],
        stats: { filesProcessed: 0, classesFound: 0, endpointsFound: 0 },
        error: String(error)
      };
    }
  }, []);

  const getGraphData = useCallback(async (): Promise<CodeGraph | { error: string }> => {
    logger.debug("getGraphData called");
    try {
      const result = await ipc.DocmakerAPI.get_graph_data();
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("getGraphData error:", parsed.error);
      } else {
        logger.debug("getGraphData success: nodes=%d, edges=%d", parsed.nodes?.length, parsed.edges?.length);
      }
      return parsed;
    } catch (error) {
      logger.error("getGraphData failed:", error);
      return { error: String(error) };
    }
  }, []);

  const parseOnly = useCallback(async (path: string): Promise<ParseResult> => {
    logger.info("parseOnly called with path:", path);
    markStart("ipc:parseOnly");
    try {
      const result = await ipc.DocmakerAPI.parse_only(path);
      const parsed = JSON.parse(result);
      markEnd("ipc:parseOnly");
      if (parsed.error) {
        logger.error("parseOnly error:", parsed.error);
      } else {
        logger.info("parseOnly success:", parsed.stats);
      }
      return parsed;
    } catch (error) {
      markEnd("ipc:parseOnly");
      logger.error("parseOnly failed:", error);
      return {
        success: false,
        stats: { filesScanned: 0, filesParsed: 0, classesFound: 0, endpointsFound: 0 },
        graph: { nodes: [], edges: [] },
        error: String(error)
      };
    }
  }, []);

  const openFile = useCallback(async (path: string, line: number = 0): Promise<{ success: boolean; error?: string }> => {
    logger.debug("openFile called:", path, line);

    // In dev mode (Pyloid not available), fall back to vscode:// URI scheme
    if (!pyloidReadyManager.isReady()) {
      logger.info("Pyloid not ready, falling back to vscode:// URI");
      const uri = line > 0 ? `vscode://file/${path}:${line}` : `vscode://file/${path}`;
      window.open(uri);
      return { success: true };
    }

    try {
      const result = await ipc.DocmakerAPI.open_file(path, line);
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("openFile error:", parsed.error);
      } else {
        logger.debug("openFile success");
      }
      return parsed;
    } catch (error) {
      logger.error("openFile failed:", error);
      return { success: false, error: String(error) };
    }
  }, []);

  const getProjectInfo = useCallback(async (): Promise<ProjectInfo> => {
    logger.debug("getProjectInfo called");
    try {
      const result = await ipc.DocmakerAPI.get_project_info();
      const parsed = JSON.parse(result);
      logger.debug("getProjectInfo result:", parsed);
      return parsed;
    } catch (error) {
      logger.error("getProjectInfo failed:", error);
      return { loaded: false };
    }
  }, []);

  const getClassDetails = useCallback(async (classFqn: string): Promise<ClassDetails> => {
    const cached = classDetailsCache.current.get(classFqn);
    if (cached) return cached;

    logger.debug("getClassDetails called:", classFqn);
    markStart("details:fetchClass");
    try {
      const result = await ipc.DocmakerAPI.get_class_details(classFqn);
      const parsed = JSON.parse(result);
      markEnd("details:fetchClass");
      if (parsed.error) {
        logger.error("getClassDetails error:", parsed.error);
      } else {
        classDetailsCache.current.set(classFqn, parsed);
      }
      return parsed;
    } catch (error) {
      markEnd("details:fetchClass");
      logger.error("getClassDetails failed:", error);
      return {
        name: "", fqn: "", path: "", line: 0, endLine: 0,
        superclass: null, interfaces: [], modifiers: [],
        docstring: null, methods: [], fields: [],
        error: String(error)
      };
    }
  }, []);

  const getEndpointDetails = useCallback(async (endpointKey: string): Promise<EndpointDetails> => {
    const cached = endpointDetailsCache.current.get(endpointKey);
    if (cached) return cached;

    logger.debug("getEndpointDetails called:", endpointKey);
    markStart("details:fetchEndpoint");
    try {
      const result = await ipc.DocmakerAPI.get_endpoint_details(endpointKey);
      const parsed = JSON.parse(result);
      markEnd("details:fetchEndpoint");
      if (parsed.error) {
        logger.error("getEndpointDetails error:", parsed.error);
      } else {
        endpointDetailsCache.current.set(endpointKey, parsed);
      }
      return parsed;
    } catch (error) {
      markEnd("details:fetchEndpoint");
      logger.error("getEndpointDetails failed:", error);
      return {
        httpMethod: "", path: "", handlerClass: "", handlerMethod: "",
        filePath: "", line: 0, parameters: [], requestBody: null,
        responseType: null, description: null,
        error: String(error)
      };
    }
  }, []);

  const getSettings = useCallback(async (): Promise<Record<string, unknown>> => {
    logger.debug("getSettings called");
    try {
      const result = await ipc.DocmakerAPI.get_settings();
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("getSettings error:", parsed.error);
      }
      return parsed;
    } catch (error) {
      logger.error("getSettings failed:", error);
      return { error: String(error) };
    }
  }, []);

  const saveSettings = useCallback(async (settings: Record<string, unknown>): Promise<{ success: boolean; error?: string }> => {
    logger.debug("saveSettings called");
    try {
      const result = await ipc.DocmakerAPI.save_settings_ipc(JSON.stringify(settings));
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("saveSettings error:", parsed.error);
      }
      return parsed;
    } catch (error) {
      logger.error("saveSettings failed:", error);
      return { success: false, error: String(error) };
    }
  }, []);

  const resetSettings = useCallback(async (): Promise<Record<string, unknown>> => {
    logger.debug("resetSettings called");
    try {
      const result = await ipc.DocmakerAPI.reset_settings_ipc();
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("resetSettings error:", parsed.error);
      }
      return parsed;
    } catch (error) {
      logger.error("resetSettings failed:", error);
      return { error: String(error) };
    }
  }, []);

  const resizeWindow = useCallback(async (width: number, height: number): Promise<{ success: boolean; error?: string }> => {
    logger.debug("resizeWindow called:", width, height);
    try {
      const result = await ipc.DocmakerAPI.resize_window(width, height);
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("resizeWindow error:", parsed.error);
      } else {
        logger.info("Window resized to:", width, height);
      }
      return parsed;
    } catch (error) {
      logger.error("resizeWindow failed:", error);
      return { success: false, error: String(error) };
    }
  }, []);

  const getWindowSize = useCallback(async (): Promise<{ width: number; height: number; error?: string }> => {
    logger.debug("getWindowSize called");
    try {
      const result = await ipc.DocmakerAPI.get_window_size();
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("getWindowSize error:", parsed.error);
      }
      return parsed;
    } catch (error) {
      logger.error("getWindowSize failed:", error);
      return { width: 0, height: 0, error: String(error) };
    }
  }, []);

  const getSourceSnippet = useCallback(async (
    path: string,
    startLine: number,
    endLine: number
  ): Promise<SourceSnippet> => {
    logger.debug("getSourceSnippet called:", path, startLine, endLine);
    try {
      const result = await ipc.DocmakerAPI.get_source_snippet(path, startLine, endLine);
      const parsed = JSON.parse(result);
      if (parsed.error) {
        logger.error("getSourceSnippet error:", parsed.error);
      }
      return parsed;
    } catch (error) {
      logger.error("getSourceSnippet failed:", error);
      return {
        lines: [],
        startLine,
        endLine,
        totalLines: 0,
        path,
        error: String(error),
      };
    }
  }, []);

  const clearCaches = useCallback(() => {
    classDetailsCache.current.clear();
    endpointDetailsCache.current.clear();
  }, []);

  return {
    isAvailable,
    selectFolder,
    scanProject,
    generateDocs,
    getGraphData,
    parseOnly,
    openFile,
    getProjectInfo,
    getClassDetails,
    getEndpointDetails,
    getSourceSnippet,
    getSettings,
    saveSettings,
    resetSettings,
    resizeWindow,
    getWindowSize,
    clearCaches,
  };
}
