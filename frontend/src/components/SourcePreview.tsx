import { memo, useState, useCallback } from "react";
import hljs from "highlight.js/lib/core";
import java from "highlight.js/lib/languages/java";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import javascript from "highlight.js/lib/languages/javascript";
import kotlin from "highlight.js/lib/languages/kotlin";
import go from "highlight.js/lib/languages/go";
import xml from "highlight.js/lib/languages/xml";
import jsonLang from "highlight.js/lib/languages/json";
import yaml from "highlight.js/lib/languages/yaml";
import css from "highlight.js/lib/languages/css";
import sql from "highlight.js/lib/languages/sql";
import bash from "highlight.js/lib/languages/bash";
import "highlight.js/styles/github-dark.css";
import type { SourceSnippet } from "../types/graph";
import { usePyloid } from "../hooks/usePyloid";

// Register languages
hljs.registerLanguage("java", java);
hljs.registerLanguage("python", python);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("kotlin", kotlin);
hljs.registerLanguage("go", go);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("html", xml);
hljs.registerLanguage("json", jsonLang);
hljs.registerLanguage("yaml", yaml);
hljs.registerLanguage("css", css);
hljs.registerLanguage("sql", sql);
hljs.registerLanguage("bash", bash);

const EXT_TO_LANG: Record<string, string> = {
  ".java": "java",
  ".py": "python",
  ".ts": "typescript",
  ".tsx": "typescript",
  ".js": "javascript",
  ".jsx": "javascript",
  ".kt": "kotlin",
  ".go": "go",
  ".xml": "xml",
  ".html": "html",
  ".json": "json",
  ".yml": "yaml",
  ".yaml": "yaml",
  ".css": "css",
  ".sql": "sql",
  ".sh": "bash",
};

function detectLanguage(filePath: string): string {
  const dot = filePath.lastIndexOf(".");
  if (dot === -1) return "plaintext";
  const ext = filePath.slice(dot).toLowerCase();
  return EXT_TO_LANG[ext] || "plaintext";
}

function escapeHtml(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

interface SourcePreviewProps {
  filePath: string;
  startLine: number;
  endLine: number;
  label?: string;
}

export const SourcePreview = memo(function SourcePreview({
  filePath,
  startLine,
  endLine,
  label,
}: SourcePreviewProps) {
  const [snippet, setSnippet] = useState<SourceSnippet | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const { getSourceSnippet } = usePyloid();

  const fetchSnippet = useCallback(async () => {
    if (snippet || loading) return;
    setLoading(true);
    try {
      const result = await getSourceSnippet(filePath, startLine, endLine);
      if (!result.error) {
        setSnippet(result);
      }
    } finally {
      setLoading(false);
    }
  }, [filePath, startLine, endLine, getSourceSnippet, snippet, loading]);

  const handleToggle = useCallback(() => {
    const next = !isOpen;
    setIsOpen(next);
    if (next && !snippet && !loading) {
      fetchSnippet();
    }
  }, [isOpen, snippet, loading, fetchSnippet]);

  const lineCount = endLine - startLine + 1;
  const language = detectLanguage(filePath);

  return (
    <div className="mt-1">
      <button
        onClick={handleToggle}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 transition-colors"
      >
        <svg
          className={`w-3 h-3 transition-transform ${isOpen ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4" />
        </svg>
        {label || "Source"}
        <span className="text-gray-600">
          L{startLine}{lineCount > 1 ? `\u2013${endLine}` : ""}
        </span>
      </button>

      {isOpen && (
        <div className="mt-1 rounded border border-gray-700 overflow-hidden">
          {loading ? (
            <div className="flex items-center justify-center py-3 bg-gray-900">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          ) : snippet ? (
            <div className="overflow-x-auto">
              <table className="w-full text-xs leading-relaxed">
                <tbody>
                  {snippet.source.split("\n").map((line, i) => (
                    <tr key={i} className="hover:bg-gray-800/50">
                      <td className="select-none text-right pr-3 pl-2 text-gray-600 border-r border-gray-700/50 bg-gray-900/50 w-1 whitespace-nowrap font-mono">
                        {snippet.startLine + i}
                      </td>
                      <td className="pl-3 pr-2 whitespace-pre font-mono">
                        <code
                          className="!bg-transparent !p-0"
                          dangerouslySetInnerHTML={{
                            __html: hljs.getLanguage(language)
                              ? hljs.highlight(line, { language }).value
                              : escapeHtml(line),
                          }}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
});
