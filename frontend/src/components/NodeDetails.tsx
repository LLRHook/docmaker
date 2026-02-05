import { useEffect, useState } from "react";
import type { GraphNode, ClassDetails, EndpointDetails } from "../types/graph";
import { usePyloid } from "../hooks/usePyloid";

interface NodeDetailsProps {
  node: GraphNode | null;
  onClose: () => void;
  onOpenFile: (path: string, line: number) => void;
}

export function NodeDetails({ node, onClose, onOpenFile }: NodeDetailsProps) {
  const [classDetails, setClassDetails] = useState<ClassDetails | null>(null);
  const [endpointDetails, setEndpointDetails] = useState<EndpointDetails | null>(null);
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

  if (!node) return null;

  const handleOpenFile = () => {
    const path = node.metadata.path || node.metadata.filePath;
    const line = node.metadata.line || 0;
    if (path) {
      onOpenFile(path, line);
    }
  };

  return (
    <div className="w-80 bg-gray-800 border-l border-gray-700 flex flex-col h-full">
      {/* Header */}
      <div className="p-3 border-b border-gray-700 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <NodeTypeIcon type={node.type} />
          <h2 className="font-semibold text-gray-100 truncate">{node.label}</h2>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-gray-400 hover:text-gray-200 hover:bg-gray-700 rounded"
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
            {/* Basic info */}
            <div className="mb-4">
              <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Details</h3>
              <dl className="space-y-1 text-sm">
                {node.metadata.fqn && (
                  <div>
                    <dt className="text-gray-500">Full Name</dt>
                    <dd className="text-gray-300 break-all">{node.metadata.fqn}</dd>
                  </div>
                )}
                {node.metadata.category && (
                  <div>
                    <dt className="text-gray-500">Category</dt>
                    <dd className="text-gray-300 capitalize">{node.metadata.category}</dd>
                  </div>
                )}
                {node.metadata.package && (
                  <div>
                    <dt className="text-gray-500">Package</dt>
                    <dd className="text-gray-300">{node.metadata.package}</dd>
                  </div>
                )}
                {(node.metadata.path || node.metadata.relativePath) && (
                  <div>
                    <dt className="text-gray-500">File</dt>
                    <dd className="text-gray-300 break-all">
                      {node.metadata.relativePath || node.metadata.path}
                    </dd>
                  </div>
                )}
                {node.metadata.line && (
                  <div>
                    <dt className="text-gray-500">Line</dt>
                    <dd className="text-gray-300">{node.metadata.line}</dd>
                  </div>
                )}
              </dl>
            </div>

            {/* Class details */}
            {classDetails && (
              <>
                {classDetails.superclass && (
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Extends</h3>
                    <div className="text-sm text-blue-400">{classDetails.superclass}</div>
                  </div>
                )}

                {classDetails.interfaces.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Implements</h3>
                    <div className="flex flex-wrap gap-1">
                      {classDetails.interfaces.map((iface) => (
                        <span key={iface} className="px-2 py-0.5 bg-purple-900/50 text-purple-300 text-xs rounded">
                          {iface}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {classDetails.fields.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">
                      Fields ({classDetails.fields.length})
                    </h3>
                    <div className="space-y-1">
                      {classDetails.fields.map((field) => (
                        <div key={field.name} className="text-sm">
                          <span className="text-gray-500">{field.type || "?"}</span>{" "}
                          <span className="text-gray-300">{field.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {classDetails.methods.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">
                      Methods ({classDetails.methods.length})
                    </h3>
                    <div className="space-y-2">
                      {classDetails.methods.map((method) => (
                        <div key={`${method.name}-${method.line}`} className="text-sm">
                          <div className="flex items-center gap-1">
                            <span className="text-gray-500">{method.returnType || "void"}</span>
                            <span className="text-gray-200 font-medium">{method.name}</span>
                            <span className="text-gray-500">()</span>
                          </div>
                          {method.modifiers.length > 0 && (
                            <div className="flex gap-1 mt-0.5">
                              {method.modifiers.map((mod) => (
                                <span key={mod} className="text-xs text-gray-500">{mod}</span>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}

            {/* Endpoint details */}
            {endpointDetails && (
              <>
                <div className="mb-4">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Endpoint</h3>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 text-xs font-bold rounded ${getMethodColor(endpointDetails.httpMethod)}`}>
                      {endpointDetails.httpMethod}
                    </span>
                    <span className="text-sm text-gray-300">{endpointDetails.path}</span>
                  </div>
                </div>

                <div className="mb-4">
                  <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Handler</h3>
                  <div className="text-sm text-gray-300">
                    {endpointDetails.handlerClass}.{endpointDetails.handlerMethod}()
                  </div>
                </div>

                {endpointDetails.parameters.length > 0 && (
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Parameters</h3>
                    <div className="space-y-1">
                      {endpointDetails.parameters.map((param) => (
                        <div key={param.name} className="text-sm">
                          <span className="text-gray-500">{param.type || "?"}</span>{" "}
                          <span className="text-gray-300">{param.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {endpointDetails.responseType && (
                  <div className="mb-4">
                    <h3 className="text-xs font-semibold text-gray-400 uppercase mb-2">Response</h3>
                    <div className="text-sm text-gray-300">{endpointDetails.responseType}</div>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </div>

      {/* Footer actions */}
      <div className="p-3 border-t border-gray-700">
        <button
          onClick={handleOpenFile}
          disabled={!node.metadata.path && !node.metadata.filePath}
          className="w-full px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 text-white text-sm rounded flex items-center justify-center gap-2"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
          Open in Editor
        </button>
      </div>
    </div>
  );
}

function NodeTypeIcon({ type }: { type: string }) {
  const colors: Record<string, string> = {
    class: "bg-blue-500",
    interface: "bg-purple-500",
    endpoint: "bg-green-500",
    package: "bg-gray-500",
    file: "bg-orange-500",
  };

  return <span className={`w-3 h-3 rounded ${colors[type] || "bg-gray-500"}`} />;
}

function getMethodColor(method: string): string {
  const colors: Record<string, string> = {
    GET: "bg-green-600 text-green-100",
    POST: "bg-blue-600 text-blue-100",
    PUT: "bg-amber-600 text-amber-100",
    PATCH: "bg-amber-600 text-amber-100",
    DELETE: "bg-red-600 text-red-100",
  };
  return colors[method.toUpperCase()] || "bg-gray-600 text-gray-100";
}
