import { useCallback } from "react";
import type {
  ScanResult,
  GenerateResult,
  ParseResult,
  ProjectInfo,
  ClassDetails,
  EndpointDetails,
  CodeGraph,
} from "../types/graph";

interface GenerateOptions {
  incremental?: boolean;
  useLlm?: boolean;
}

function getApi() {
  if (typeof window !== "undefined" && window.pyloid?.DocmakerAPI) {
    return window.pyloid.DocmakerAPI;
  }
  return null;
}

export function usePyloid() {
  const isAvailable = useCallback(() => {
    return getApi() !== null;
  }, []);

  const scanProject = useCallback(async (path: string): Promise<ScanResult> => {
    const api = getApi();
    if (!api) {
      return { projectPath: "", files: [], stats: { totalFiles: 0, byLanguage: {}, byCategory: {} }, error: "Pyloid API not available" };
    }
    const result = await api.scan_project(path);
    return JSON.parse(result);
  }, []);

  const generateDocs = useCallback(async (options: GenerateOptions = {}): Promise<GenerateResult> => {
    const api = getApi();
    if (!api) {
      return { success: false, generatedFiles: [], stats: { filesProcessed: 0, classesFound: 0, endpointsFound: 0 }, error: "Pyloid API not available" };
    }
    const result = await api.generate_docs(JSON.stringify(options));
    return JSON.parse(result);
  }, []);

  const getGraphData = useCallback(async (): Promise<CodeGraph | { error: string }> => {
    const api = getApi();
    if (!api) {
      return { error: "Pyloid API not available" };
    }
    const result = await api.get_graph_data();
    return JSON.parse(result);
  }, []);

  const parseOnly = useCallback(async (path: string): Promise<ParseResult> => {
    const api = getApi();
    if (!api) {
      return {
        success: false,
        stats: { filesScanned: 0, filesParsed: 0, classesFound: 0, endpointsFound: 0 },
        graph: { nodes: [], edges: [] },
        error: "Pyloid API not available"
      };
    }
    const result = await api.parse_only(path);
    return JSON.parse(result);
  }, []);

  const openFile = useCallback(async (path: string, line: number = 0): Promise<{ success: boolean; error?: string }> => {
    const api = getApi();
    if (!api) {
      return { success: false, error: "Pyloid API not available" };
    }
    const result = await api.open_file(path, line);
    return JSON.parse(result);
  }, []);

  const getProjectInfo = useCallback(async (): Promise<ProjectInfo> => {
    const api = getApi();
    if (!api) {
      return { loaded: false };
    }
    const result = await api.get_project_info();
    return JSON.parse(result);
  }, []);

  const getClassDetails = useCallback(async (classFqn: string): Promise<ClassDetails> => {
    const api = getApi();
    if (!api) {
      return {
        name: "", fqn: "", path: "", line: 0, endLine: 0,
        superclass: null, interfaces: [], modifiers: [],
        docstring: null, methods: [], fields: [],
        error: "Pyloid API not available"
      };
    }
    const result = await api.get_class_details(classFqn);
    return JSON.parse(result);
  }, []);

  const getEndpointDetails = useCallback(async (endpointKey: string): Promise<EndpointDetails> => {
    const api = getApi();
    if (!api) {
      return {
        httpMethod: "", path: "", handlerClass: "", handlerMethod: "",
        filePath: "", line: 0, parameters: [], requestBody: null,
        responseType: null, description: null,
        error: "Pyloid API not available"
      };
    }
    const result = await api.get_endpoint_details(endpointKey);
    return JSON.parse(result);
  }, []);

  return {
    isAvailable,
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
