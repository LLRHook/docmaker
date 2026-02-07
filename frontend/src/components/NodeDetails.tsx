import { memo, useEffect, useState, useCallback, useMemo } from "react";
import type { GraphNode, ClassDetails, EndpointDetails, FieldInfo, MethodInfo, CategorizedParameter, ParameterCategory, AnnotationInfo } from "../types/graph";
import { usePyloid } from "../hooks/usePyloid";

function getDefaultForType(javaType: string): unknown {
  const normalized = javaType.trim();

  if (/^(String|CharSequence)$/i.test(normalized)) return "string";
  if (/^(int|Integer|short|Short|byte|Byte)$/i.test(normalized)) return 0;
  if (/^(long|Long)$/i.test(normalized)) return 0;
  if (/^(double|Double|float|Float|BigDecimal)$/i.test(normalized)) return 0.0;
  if (/^(boolean|Boolean)$/i.test(normalized)) return false;
  if (/^LocalDate$/i.test(normalized)) return "2024-01-01";
  if (/^(LocalDateTime|ZonedDateTime|Instant)$/i.test(normalized)) return "2024-01-01T00:00:00Z";
  if (/^UUID$/i.test(normalized)) return "00000000-0000-0000-0000-000000000000";

  const listMatch = normalized.match(/^(?:List|Set|Collection)<(.+)>$/);
  if (listMatch) return [getDefaultForType(listMatch[1])];

  const mapMatch = normalized.match(/^Map<(.+),\s*(.+)>$/);
  if (mapMatch) return {};

  return {};
}

function buildSampleJson(fields: FieldInfo[]): Record<string, unknown> {
  const result: Record<string, unknown> = {};
  for (const field of fields) {
    if (field.modifiers.includes("static")) continue;
    result[field.name] = getDefaultForType(field.type || "Object");
  }
  return result;
}

function categorizeParameter(param: { name: string; type: string | null; description: string | null }): CategorizedParameter {
  const desc = param.description || "";
  let category: ParameterCategory = "query";

  if (desc.includes("@PathVariable")) category = "path";
  else if (desc.includes("@RequestParam")) category = "query";
  else if (desc.includes("@RequestBody")) category = "body";
  else if (desc.includes("@RequestHeader")) category = "header";

  return { name: param.name, type: param.type, description: param.description, category };
}

function methodBgColor(method: string): string {
  const colors: Record<string, string> = {
    GET: "bg-green-900/40 border-green-600/50",
    POST: "bg-blue-900/40 border-blue-600/50",
    PUT: "bg-amber-900/40 border-amber-600/50",
    PATCH: "bg-amber-900/40 border-amber-600/50",
    DELETE: "bg-red-900/40 border-red-600/50",
  };
  return colors[method.toUpperCase()] || "bg-c-bg/40 border-c-line-soft/50";
}

interface NodeDetailsProps {
  node: GraphNode | null;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
  onClose: () => void;
  onOpenFile: (path: string, line: number) => void;
  onNavigateToNode: (nodeId: string) => void;
  allNodes: GraphNode[];
}

export const NodeDetails = memo(function NodeDetails({
  node,
  isCollapsed,
  onToggleCollapse,
  onClose,
  onOpenFile,
  onNavigateToNode,
  allNodes,
}: NodeDetailsProps) {
  const [classDetails, setClassDetails] = useState<ClassDetails | null>(null);
  const [endpointDetails, setEndpointDetails] = useState<EndpointDetails | null>(null);
  const [requestBodyDetails, setRequestBodyDetails] = useState<ClassDetails | null>(null);
  const [responseTypeDetails, setResponseTypeDetails] = useState<ClassDetails | null>(null);
  const [loading, setLoading] = useState(false);
  const { getClassDetails, getEndpointDetails } = usePyloid();

  useEffect(() => {
    if (!node) {
      setClassDetails(null);
      setEndpointDetails(null);
      return;
    }

    const fetchDetails = async () => {
      setLoading(true);
      try {
        if (node.type === "class" || node.type === "interface") {
          const fqn = node.metadata.fqn || node.label;
          const details = await getClassDetails(fqn);
          if (!details.error) {
            setClassDetails(details);
            setEndpointDetails(null);
          }
        } else if (node.type === "endpoint") {
          const key = `${node.metadata.method}:${node.metadata.path}`;
          const details = await getEndpointDetails(key);
          if (!details.error) {
            setEndpointDetails(details);
            setClassDetails(null);
          }
        }
      } catch (err) {
        console.error("Error fetching details:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [node, getClassDetails, getEndpointDetails]);

  useEffect(() => {
    setRequestBodyDetails(null);
    setResponseTypeDetails(null);

    if (!endpointDetails) return;

    const fetchRelatedClasses = async () => {
      const promises: Promise<void>[] = [];

      if (endpointDetails.requestBody) {
        promises.push(
          getClassDetails(endpointDetails.requestBody)
            .then((details) => { if (!details.error) setRequestBodyDetails(details); })
            .catch(() => { /* ignore */ })
        );
      }

      if (endpointDetails.responseType) {
        promises.push(
          getClassDetails(endpointDetails.responseType)
            .then((details) => { if (!details.error) setResponseTypeDetails(details); })
            .catch(() => { /* ignore */ })
        );
      }

      await Promise.all(promises);
    };

    fetchRelatedClasses();
  }, [endpointDetails, getClassDetails]);

  const categorizedParams = useMemo(() => {
    if (!endpointDetails) return { path: [], query: [], header: [], body: [] };

    const grouped: Record<ParameterCategory, CategorizedParameter[]> = {
      path: [], query: [], header: [], body: [],
    };

    for (const param of endpointDetails.parameters) {
      const categorized = categorizeParameter(param);
      grouped[categorized.category].push(categorized);
    }

    return grouped;
  }, [endpointDetails]);

  // Find a node by name/fqn to enable navigation
  const findNodeByName = useCallback(
    (name: string): GraphNode | null => {
      // Try exact match on label first
      let found = allNodes.find((n) => n.label === name);
      if (found) return found;

      // Try FQN match
      found = allNodes.find((n) => n.metadata.fqn === name);
      if (found) return found;

      // Try partial match (class name without package)
      const simpleName = name.includes(".") ? name.split(".").pop() : name;
      found = allNodes.find((n) => n.label === simpleName);
      return found || null;
    },
    [allNodes]
  );

  const handleOpenFile = () => {
    if (!node) return;
    const path = node.metadata.path || node.metadata.filePath;
    const line = node.metadata.line || 0;
    if (path) {
      onOpenFile(path, line);
    }
  };

  // Render a clickable link for a type name
  const renderTypeLink = (typeName: string, className?: string) => {
    const targetNode = findNodeByName(typeName);
    if (targetNode) {
      return (
        <button
          onClick={() => onNavigateToNode(targetNode.id)}
          className={`text-blue-400 hover:text-blue-300 hover:underline cursor-pointer ${className || ""}`}
        >
          {typeName}
        </button>
      );
    }
    return <span className={className}>{typeName}</span>;
  };

  // Collapsed state - just show the toggle button on the edge
  if (isCollapsed) {
    return (
      <div className="relative">
        <button
          onClick={onToggleCollapse}
          className="absolute right-0 top-1/2 -translate-y-1/2 w-6 h-16 bg-c-surface border border-c-line border-r-0 rounded-l-md flex items-center justify-center text-c-text-dim hover:text-c-text hover:bg-c-element z-10"
          title="Expand details panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
      </div>
    );
  }

  // No node selected - show empty state with collapse button
  if (!node) {
    return (
      <div className="w-full bg-c-surface border-l border-c-line flex flex-col h-full relative">
        {/* Collapse toggle on edge */}
        <button
          onClick={onToggleCollapse}
          className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-16 bg-c-surface border border-c-line rounded-l-md flex items-center justify-center text-c-text-dim hover:text-c-text hover:bg-c-element z-10"
          title="Collapse details panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
        </button>

        <div className="flex items-center justify-center h-full text-c-text-faint">
          <div className="text-center p-6">
            <svg
              className="w-12 h-12 mx-auto mb-3 opacity-50"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <p className="text-sm">Select a node to view details</p>
            <p className="text-xs text-c-text-faint mt-1">Click on a class, interface, or endpoint</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full bg-c-surface border-l border-c-line flex flex-col h-full relative">
      {/* Collapse toggle on edge */}
      <button
        onClick={onToggleCollapse}
        className="absolute -left-3 top-1/2 -translate-y-1/2 w-6 h-16 bg-c-surface border border-c-line rounded-l-md flex items-center justify-center text-c-text-dim hover:text-c-text hover:bg-c-element z-10"
        title="Collapse details panel"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
      </button>

      {/* Header */}
      <div className="p-3 border-b border-c-line flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <NodeTypeIcon type={node.type} />
          <h2 className="font-semibold text-c-text truncate">{node.label}</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-c-text-dim hover:text-c-text hover:bg-c-element rounded-sm shrink-0"
          title="Close"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3">
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
          </div>
        ) : (
          <>
            {/* Basic info section */}
            <Section title="Overview">
              <InfoItem label="Type" value={<span className="capitalize">{node.type}</span>} />
              {node.metadata.fqn && <InfoItem label="Full Name" value={node.metadata.fqn} mono />}
              {node.metadata.category && (
                <InfoItem
                  label="Category"
                  value={<CategoryBadge category={node.metadata.category} />}
                />
              )}
              {node.metadata.package && (
                <InfoItem label="Package" value={node.metadata.package} mono />
              )}
            </Section>

            {/* File location */}
            {(node.metadata.path || node.metadata.relativePath) && (
              <Section title="Location">
                <div className="text-sm">
                  <button
                    onClick={handleOpenFile}
                    className="text-blue-400 hover:text-blue-300 hover:underline text-left break-all"
                  >
                    {node.metadata.relativePath || node.metadata.path}
                    {node.metadata.line && <span className="text-c-text-faint">:{node.metadata.line}</span>}
                  </button>
                </div>
              </Section>
            )}

            {/* Class-specific details */}
            {classDetails && (
              <>
                {/* Inheritance */}
                {(classDetails.superclass || classDetails.interfaces.length > 0) && (
                  <Section title="Inheritance">
                    {classDetails.superclass && (
                      <div className="mb-2">
                        <span className="text-xs text-c-text-faint mr-2">extends</span>
                        {renderTypeLink(classDetails.superclass, "text-sm")}
                      </div>
                    )}
                    {classDetails.interfaces.length > 0 && (
                      <div>
                        <span className="text-xs text-c-text-faint mr-2">implements</span>
                        <div className="flex flex-wrap gap-1 mt-1">
                          {classDetails.interfaces.map((iface) => (
                            <span
                              key={iface}
                              className="px-2 py-0.5 bg-purple-900/50 text-purple-300 text-xs rounded-sm"
                            >
                              {renderTypeLink(iface)}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </Section>
                )}

                {/* Fields */}
                {classDetails.fields.length > 0 && (
                  <Section title={`Fields (${classDetails.fields.length})`} collapsible defaultOpen={false}>
                    <div className="space-y-1.5">
                      {classDetails.fields.map((field) => (
                        <div key={field.name} className="text-sm">
                          {field.annotations && field.annotations.length > 0 && (
                            <AnnotationBadges annotations={field.annotations} />
                          )}
                          <div className="flex items-baseline gap-1.5">
                            <span className="text-c-text-faint text-xs">
                              {renderTypeLink(field.type || "?", "text-c-text-faint")}
                            </span>
                            <span className="text-c-text">{field.name}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </Section>
                )}

                {/* Methods */}
                {classDetails.methods.length > 0 && (
                  <Section title={`Methods (${classDetails.methods.length})`} collapsible defaultOpen>
                    <div className="space-y-2">
                      {classDetails.methods.map((method) => (
                        <div key={`${method.name}-${method.line}`} className="text-sm">
                          {method.annotations && method.annotations.length > 0 && (
                            <AnnotationBadges annotations={method.annotations} />
                          )}
                          <MethodSignature method={method} renderTypeLink={renderTypeLink} />
                          {method.docstring && (
                            <p className="text-xs text-c-text-faint italic mt-0.5 truncate" title={method.docstring}>
                              {method.docstring}
                            </p>
                          )}
                          {method.modifiers.length > 0 && (
                            <div className="flex gap-1 mt-0.5">
                              {method.modifiers.map((mod) => (
                                <span
                                  key={mod}
                                  className="text-xs text-c-text-faint bg-c-element/50 px-1 rounded"
                                >
                                  {mod}
                                </span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </Section>
                )}
              </>
            )}

            {/* Endpoint-specific details */}
            {endpointDetails && (
              <>
                {/* Swagger-style banner */}
                <div className={`rounded border p-3 mb-4 ${methodBgColor(endpointDetails.httpMethod)}`}>
                  <div className="flex items-center gap-2">
                    <HttpMethodBadge method={endpointDetails.httpMethod} />
                    <span className="text-sm text-c-text font-mono font-medium">{endpointDetails.path}</span>
                  </div>
                  {endpointDetails.description && (
                    <p className="text-sm text-c-text-dim mt-2">{endpointDetails.description}</p>
                  )}
                </div>

                <Section title="Handler">
                  <div className="text-sm">
                    {renderTypeLink(endpointDetails.handlerClass, "text-blue-400")}
                    <span className="text-c-text-faint">.</span>
                    <span className="text-c-text">{endpointDetails.handlerMethod}</span>
                    <span className="text-c-text-faint">()</span>
                  </div>
                </Section>

                {categorizedParams.path.length > 0 && (
                  <Section title="Path Parameters">
                    <ParameterTable params={categorizedParams.path} renderTypeLink={renderTypeLink} />
                  </Section>
                )}

                {categorizedParams.query.length > 0 && (
                  <Section title="Query Parameters">
                    <ParameterTable params={categorizedParams.query} renderTypeLink={renderTypeLink} />
                  </Section>
                )}

                {categorizedParams.header.length > 0 && (
                  <Section title="Header Parameters">
                    <ParameterTable params={categorizedParams.header} renderTypeLink={renderTypeLink} />
                  </Section>
                )}

                {endpointDetails.requestBody && (
                  <Section title="Request Body" collapsible defaultOpen>
                    <SampleJsonBlock
                      typeName={endpointDetails.requestBody}
                      classDetails={requestBodyDetails}
                      renderTypeLink={renderTypeLink}
                    />
                  </Section>
                )}

                {endpointDetails.responseType && (
                  <Section title="Response" collapsible defaultOpen>
                    <SampleJsonBlock
                      typeName={endpointDetails.responseType}
                      classDetails={responseTypeDetails}
                      renderTypeLink={renderTypeLink}
                    />
                  </Section>
                )}

                <Section title="Example Request" collapsible defaultOpen={false}>
                  <ExampleRequestBlock endpoint={endpointDetails} requestBodyDetails={requestBodyDetails} />
                </Section>
              </>
            )}
          </>
        )}
      </div>

      {/* Footer actions */}
      <div className="p-3 border-t border-c-line">
        <button
          onClick={handleOpenFile}
          disabled={!node.metadata.path && !node.metadata.filePath}
          className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-c-element disabled:text-c-text-faint text-white text-sm rounded-sm flex items-center justify-center gap-2 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
            />
          </svg>
          Open in Editor
        </button>
      </div>
    </div>
  );
});

// --- Helper Components ---

function NodeTypeIcon({ type }: { type: string }) {
  const colors: Record<string, string> = {
    class: "bg-blue-500",
    interface: "bg-purple-500",
    endpoint: "bg-green-500",
    package: "bg-gray-500",
    file: "bg-orange-500",
  };

  return <span className={`w-3 h-3 rounded-sm shrink-0 ${colors[type] || "bg-gray-500"}`} />;
}

function CategoryBadge({ category }: { category: string }) {
  const colors: Record<string, string> = {
    backend: "bg-blue-900/50 text-blue-300",
    frontend: "bg-green-900/50 text-green-300",
    config: "bg-yellow-900/50 text-yellow-300",
    test: "bg-purple-900/50 text-purple-300",
    unknown: "bg-c-element text-c-text-dim",
  };

  return (
    <span className={`px-2 py-0.5 text-xs rounded-sm capitalize ${colors[category] || colors.unknown}`}>
      {category}
    </span>
  );
}

function HttpMethodBadge({ method }: { method: string }) {
  const colors: Record<string, string> = {
    GET: "bg-green-600 text-green-100",
    POST: "bg-blue-600 text-blue-100",
    PUT: "bg-amber-600 text-amber-100",
    PATCH: "bg-amber-600 text-amber-100",
    DELETE: "bg-red-600 text-red-100",
  };

  return (
    <span
      className={`px-2 py-0.5 text-xs font-bold rounded-sm ${colors[method.toUpperCase()] || "bg-c-hover text-c-text"}`}
    >
      {method}
    </span>
  );
}

function InfoItem({
  label,
  value,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-xs text-c-text-faint">{label}</dt>
      <dd className={`text-sm text-c-text-sub break-all ${mono ? "font-mono text-xs" : ""}`}>{value}</dd>
    </div>
  );
}

interface SectionProps {
  title: string;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

function Section({ title, children, collapsible = false, defaultOpen = true }: SectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="mb-4">
      {collapsible ? (
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center gap-1 text-xs font-semibold text-c-text-dim uppercase mb-2 hover:text-c-text-sub w-full text-left"
        >
          <svg
            className={`w-3 h-3 transition-transform ${isOpen ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
          </svg>
          {title}
        </button>
      ) : (
        <h3 className="text-xs font-semibold text-c-text-dim uppercase mb-2">{title}</h3>
      )}
      {(!collapsible || isOpen) && <div className="space-y-1.5">{children}</div>}
    </div>
  );
}

function AnnotationBadges({ annotations }: { annotations: AnnotationInfo[] }) {
  return (
    <div className="flex flex-wrap gap-1 mb-0.5">
      {annotations.map((ann) => (
        <span
          key={ann.name}
          className="text-xs text-amber-300 bg-amber-900/40 px-1.5 py-0.5 rounded"
        >
          @{ann.name}
        </span>
      ))}
    </div>
  );
}

function MethodSignature({
  method,
  renderTypeLink,
}: {
  method: MethodInfo;
  renderTypeLink: (typeName: string, className?: string) => React.ReactNode;
}) {
  return (
    <div className="flex items-baseline gap-1.5 flex-wrap">
      <span className="text-c-text-faint text-xs">
        {renderTypeLink(method.returnType || "void", "text-c-text-faint")}
      </span>
      <span className="text-c-text font-medium">{method.name}</span>
      <span className="text-c-text-faint">(</span>
      {method.parameters.map((param, i) => (
        <span key={param.name} className="text-xs">
          {renderTypeLink(param.type || "?", "text-c-text-faint")}
          <span className="text-c-text-dim ml-0.5">{param.name}</span>
          {i < method.parameters.length - 1 && <span className="text-c-text-faint">, </span>}
        </span>
      ))}
      <span className="text-c-text-faint">)</span>
    </div>
  );
}

function stripAnnotationPrefix(description: string | null): string {
  if (!description) return "";
  return description.replace(/^@\w+\s*/, "");
}

function ParameterTable({
  params,
  renderTypeLink,
}: {
  params: CategorizedParameter[];
  renderTypeLink: (typeName: string, className?: string) => React.ReactNode;
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-xs text-c-text-faint border-b border-c-line">
          <th className="text-left py-1 pr-2 font-medium">Name</th>
          <th className="text-left py-1 pr-2 font-medium">Type</th>
          <th className="text-left py-1 font-medium">Description</th>
        </tr>
      </thead>
      <tbody>
        {params.map((param) => (
          <tr key={param.name} className="border-b border-c-line/50">
            <td className="py-1.5 pr-2 text-c-text font-mono text-xs">{param.name}</td>
            <td className="py-1.5 pr-2 text-c-text-dim text-xs">
              {renderTypeLink(param.type || "?", "text-c-text-dim")}
            </td>
            <td className="py-1.5 text-c-text-faint text-xs">{stripAnnotationPrefix(param.description)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function SampleJsonBlock({
  typeName,
  classDetails,
  renderTypeLink,
}: {
  typeName: string;
  classDetails: ClassDetails | null;
  renderTypeLink: (typeName: string, className?: string) => React.ReactNode;
}) {
  const sampleJson = classDetails && classDetails.fields.length > 0
    ? JSON.stringify(buildSampleJson(classDetails.fields), null, 2)
    : null;

  return (
    <div>
      <div className="text-sm mb-2">
        {renderTypeLink(typeName, "text-blue-400")}
      </div>
      {sampleJson && (
        <pre className="text-xs bg-c-bg border border-c-line rounded p-2 overflow-x-auto text-c-text-sub">
          {sampleJson}
        </pre>
      )}
    </div>
  );
}

function ExampleRequestBlock({
  endpoint,
  requestBodyDetails,
}: {
  endpoint: EndpointDetails;
  requestBodyDetails: ClassDetails | null;
}) {
  const method = endpoint.httpMethod.toUpperCase();
  const hasBody = ["POST", "PUT", "PATCH"].includes(method);
  const bodyJson = hasBody && requestBodyDetails && requestBodyDetails.fields.length > 0
    ? JSON.stringify(buildSampleJson(requestBodyDetails.fields), null, 2)
    : null;

  const lines = [`${method} ${endpoint.path}`];
  if (hasBody) {
    lines.push("Content-Type: application/json");
  }
  if (bodyJson) {
    lines.push("");
    lines.push(bodyJson);
  }

  return (
    <pre className="text-xs bg-c-bg border border-c-line rounded p-2 overflow-x-auto text-c-text-sub">
      {lines.join("\n")}
    </pre>
  );
}
