export interface GraphNode {
  id: string;
  label: string;
  type: "class" | "interface" | "file" | "package" | "endpoint";
  metadata: {
    fqn?: string;
    path?: string;
    filePath?: string;
    relativePath?: string;
    language?: string;
    category?: string;
    line?: number;
    endLine?: number;
    package?: string;
    modifiers?: string[];
    superclass?: string | null;
    interfaces?: string[];
    methodCount?: number;
    fieldCount?: number;
    method?: string;
    handler?: string;
  };
}

export interface GraphEdge {
  source: string;
  target: string;
  type: "extends" | "implements" | "imports" | "calls" | "contains";
}

export interface CodeGraph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface FileInfo {
  path: string;
  language: string;
  category: string;
  size: number;
}

export interface ProjectStats {
  totalFiles: number;
  byLanguage: Record<string, number>;
  byCategory: Record<string, number>;
}

export interface ScanResult {
  projectPath: string;
  files: FileInfo[];
  stats: ProjectStats;
  error?: string;
}

export interface GenerateResult {
  success: boolean;
  generatedFiles: string[];
  stats: {
    filesProcessed: number;
    classesFound: number;
    endpointsFound: number;
  };
  error?: string;
}

export interface ParseResult {
  success: boolean;
  stats: {
    filesScanned: number;
    filesParsed: number;
    classesFound: number;
    endpointsFound: number;
  };
  graph: CodeGraph;
  error?: string;
}

export interface ProjectInfo {
  loaded: boolean;
  path?: string;
  name?: string;
  hasSymbolTable?: boolean;
  stats?: {
    files: number;
    classes: number;
    endpoints: number;
  };
}

export interface AnnotationInfo {
  name: string;
  arguments: Record<string, string>;
}

export interface MethodInfo {
  name: string;
  returnType: string | null;
  parameters: { name: string; type: string | null }[];
  modifiers: string[];
  line: number;
  endLine?: number;
  docstring?: string | null;
  annotations?: AnnotationInfo[];
}

export interface FieldInfo {
  name: string;
  type: string | null;
  modifiers: string[];
  line: number;
  annotations?: AnnotationInfo[];
}

export interface ClassDetails {
  name: string;
  fqn: string;
  path: string;
  line: number;
  endLine: number;
  superclass: string | null;
  interfaces: string[];
  modifiers: string[];
  docstring: string | null;
  methods: MethodInfo[];
  fields: FieldInfo[];
  error?: string;
}

export type ParameterCategory = "path" | "query" | "header" | "body";

export interface CategorizedParameter {
  name: string;
  type: string | null;
  description: string | null;
  category: ParameterCategory;
}

export interface SourceSnippet {
  source: string;
  startLine: number;
  endLine: number;
  totalLines: number;
  path: string;
  error?: string;
}

export interface EndpointDetails {
  httpMethod: string;
  path: string;
  handlerClass: string;
  handlerMethod: string;
  filePath: string;
  line: number;
  parameters: { name: string; type: string | null; description: string | null }[];
  requestBody: string | null;
  responseType: string | null;
  description: string | null;
  error?: string;
}
