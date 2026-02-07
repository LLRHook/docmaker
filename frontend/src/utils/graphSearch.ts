import type { GraphNode } from "../types/graph";

export interface SearchMatchResult {
  nodeId: string;
  matchType: "label" | "fqn" | "annotation" | "modifier" | "type";
}

const MODIFIERS = [
  "abstract", "final", "static", "public", "private",
  "protected", "default", "synchronized", "volatile",
  "transient", "native",
];

/**
 * Match a graph node against a search query.
 *
 * Supported query prefixes:
 * - `@` filters by annotation name (e.g. `@Controller`)
 * - `abstract`, `public`, `final`, etc. filter by modifier
 * - `type:` filters by node type (e.g. `type:class`, `type:endpoint`)
 *
 * Plain text matches against label and FQN.
 */
export function matchNodeToQuery(node: GraphNode, query: string): SearchMatchResult | null {
  const trimmed = query.trim();
  if (!trimmed) return null;

  // Annotation filter: @AnnotationName
  if (trimmed.startsWith("@")) {
    const annotationQuery = trimmed.slice(1).toLowerCase();
    if (!annotationQuery) return null;
    const fqn = node.metadata.fqn?.toLowerCase() ?? "";
    const label = node.label.toLowerCase();
    if (fqn.includes(`@${annotationQuery}`) || label.includes(`@${annotationQuery}`)) {
      return { nodeId: node.id, matchType: "annotation" };
    }
    if (label.includes(annotationQuery)) {
      return { nodeId: node.id, matchType: "annotation" };
    }
    return null;
  }

  // Type filter: type:class, type:interface, type:endpoint, etc.
  if (trimmed.toLowerCase().startsWith("type:")) {
    const typeQuery = trimmed.slice(5).toLowerCase().trim();
    if (!typeQuery) return null;
    if (node.type.toLowerCase().startsWith(typeQuery)) {
      return { nodeId: node.id, matchType: "type" };
    }
    return null;
  }

  // Modifier filter: check if query matches a known modifier
  const lowerTrimmed = trimmed.toLowerCase();
  if (MODIFIERS.includes(lowerTrimmed)) {
    const modifiers = node.metadata.modifiers ?? [];
    if (modifiers.some((m) => m.toLowerCase() === lowerTrimmed)) {
      return { nodeId: node.id, matchType: "modifier" };
    }
    return null;
  }

  // Plain text search: match label or FQN
  if (node.label.toLowerCase().includes(lowerTrimmed)) {
    return { nodeId: node.id, matchType: "label" };
  }
  if (node.metadata.fqn?.toLowerCase().includes(lowerTrimmed)) {
    return { nodeId: node.id, matchType: "fqn" };
  }

  return null;
}
