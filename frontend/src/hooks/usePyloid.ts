import { useCallback, useState, useEffect } from "react";
import type {
  ScanResult,
  GenerateResult,
  ParseResult,
  ProjectInfo,
  ClassDetails,
  EndpointDetails,
  CodeGraph,
} from "../types/graph";
import { createLogger } from "../utils/logger";

const logger = createLogger("usePyloid");

interface GenerateOptions {
  incremental?: boolean;
  useLlm?: boolean;
}

interface DocmakerAPIType {
  select_folder(): Promise<string>;
  scan_project(path: string): Promise<string>;
  generate_docs(options: string): Promise<string>;
  get_graph_data(): Promise<string>;
  parse_only(path: string): Promise<string>;
  open_file(path: string, line: number): Promise<string>;
  get_project_info(): Promise<string>;
  get_class_details(classFqn: string): Promise<string>;
  get_endpoint_details(endpointKey: string): Promise<string>;
}

// Pyloid injects IPC classes into window.ipc.ClassName
function getApi(): DocmakerAPIType | null {
  const win = window as unknown as { ipc?: { DocmakerAPI?: DocmakerAPIType } };
  if (win.ipc?.DocmakerAPI) {
    return win.ipc.DocmakerAPI;
  }
  return null;
}

export function usePyloid() {
  const [ready, setReady] = useState(() => getApi() !== null);

  // Listen for pyloidReady event (dispatched when Pyloid finishes injecting APIs)
  useEffect(() => {
    if (ready) {
      logger.info("Pyloid API already available");
      return;
    }

    const handlePyloidReady = () => {
      logger.info("pyloidReady event received");
      if (getApi() !== null) {
        setReady(true);
      }
    };

    document.addEventListener("pyloidReady", handlePyloidReady);

    // Also check immediately in case event already fired
    if (getApi() !== null) {
      logger.info("Pyloid API available on mount");
      setReady(true);
    }

    return () => {
      document.removeEventListener("pyloidReady", handlePyloidReady);
    };
  }, [ready]);

  const isAvailable = useCallback(() => {
    return ready && getApi() !== null;
  }, [ready]);

  const selectFolder = useCallback(async (): Promise<string | null> => {
    logger.debug("selectFolder called");
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return null;
    }
    const result = await api.select_folder();
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("Error selecting folder:", parsed.error);
      return null;
    }
    logger.info("Folder selected:", parsed.path);
    return parsed.path;
  }, []);

  const scanProject = useCallback(async (path: string): Promise<ScanResult> => {
    logger.info("scanProject called with path:", path);
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return { projectPath: "", files: [], stats: { totalFiles: 0, byLanguage: {}, byCategory: {} }, error: "Pyloid API not available" };
    }
    const result = await api.scan_project(path);
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("scanProject error:", parsed.error);
    } else {
      logger.info("scanProject success:", parsed.stats);
    }
    return parsed;
  }, []);

  const generateDocs = useCallback(async (options: GenerateOptions = {}): Promise<GenerateResult> => {
    logger.info("generateDocs called with options:", options);
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return { success: false, generatedFiles: [], stats: { filesProcessed: 0, classesFound: 0, endpointsFound: 0 }, error: "Pyloid API not available" };
    }
    const result = await api.generate_docs(JSON.stringify(options));
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("generateDocs error:", parsed.error);
    } else {
      logger.info("generateDocs success:", parsed.stats);
    }
    return parsed;
  }, []);

  const getGraphData = useCallback(async (): Promise<CodeGraph | { error: string }> => {
    logger.debug("getGraphData called");
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return { error: "Pyloid API not available" };
    }
    const result = await api.get_graph_data();
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("getGraphData error:", parsed.error);
    } else {
      logger.debug("getGraphData success: nodes=%d, edges=%d", parsed.nodes?.length, parsed.edges?.length);
    }
    return parsed;
  }, []);

  const parseOnly = useCallback(async (path: string): Promise<ParseResult> => {
    logger.info("parseOnly called with path:", path);
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return {
        success: false,
        stats: { filesScanned: 0, filesParsed: 0, classesFound: 0, endpointsFound: 0 },
        graph: { nodes: [], edges: [] },
        error: "Pyloid API not available"
      };
    }
    const result = await api.parse_only(path);
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("parseOnly error:", parsed.error);
    } else {
      logger.info("parseOnly success:", parsed.stats);
    }
    return parsed;
  }, []);

  const openFile = useCallback(async (path: string, line: number = 0): Promise<{ success: boolean; error?: string }> => {
    logger.debug("openFile called:", path, line);
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return { success: false, error: "Pyloid API not available" };
    }
    const result = await api.open_file(path, line);
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("openFile error:", parsed.error);
    } else {
      logger.debug("openFile success");
    }
    return parsed;
  }, []);

  const getProjectInfo = useCallback(async (): Promise<ProjectInfo> => {
    logger.debug("getProjectInfo called");
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return { loaded: false };
    }
    const result = await api.get_project_info();
    const parsed = JSON.parse(result);
    logger.debug("getProjectInfo result:", parsed);
    return parsed;
  }, []);

  const getClassDetails = useCallback(async (classFqn: string): Promise<ClassDetails> => {
    logger.debug("getClassDetails called:", classFqn);
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return {
        name: "", fqn: "", path: "", line: 0, endLine: 0,
        superclass: null, interfaces: [], modifiers: [],
        docstring: null, methods: [], fields: [],
        error: "Pyloid API not available"
      };
    }
    const result = await api.get_class_details(classFqn);
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("getClassDetails error:", parsed.error);
    }
    return parsed;
  }, []);

  const getEndpointDetails = useCallback(async (endpointKey: string): Promise<EndpointDetails> => {
    logger.debug("getEndpointDetails called:", endpointKey);
    const api = getApi();
    if (!api) {
      logger.warn("Pyloid API not available");
      return {
        httpMethod: "", path: "", handlerClass: "", handlerMethod: "",
        filePath: "", line: 0, parameters: [], requestBody: null,
        responseType: null, description: null,
        error: "Pyloid API not available"
      };
    }
    const result = await api.get_endpoint_details(endpointKey);
    const parsed = JSON.parse(result);
    if (parsed.error) {
      logger.error("getEndpointDetails error:", parsed.error);
    }
    return parsed;
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
  };
}
