import { memo, useEffect, useState, useMemo, useRef, useCallback } from "react";
import hljs from "highlight.js/lib/core";
import java from "highlight.js/lib/languages/java";
import python from "highlight.js/lib/languages/python";
import typescript from "highlight.js/lib/languages/typescript";
import javascript from "highlight.js/lib/languages/javascript";
import kotlin from "highlight.js/lib/languages/kotlin";
import xml from "highlight.js/lib/languages/xml";
import jsonLang from "highlight.js/lib/languages/json";
import yaml from "highlight.js/lib/languages/yaml";
import { usePyloid } from "../hooks/usePyloid";

// Register languages
hljs.registerLanguage("java", java);
hljs.registerLanguage("python", python);
hljs.registerLanguage("typescript", typescript);
hljs.registerLanguage("javascript", javascript);
hljs.registerLanguage("kotlin", kotlin);
hljs.registerLanguage("xml", xml);
hljs.registerLanguage("json", jsonLang);
hljs.registerLanguage("yaml", yaml);

interface SourcePreviewProps {
  filePath: string;
  startLine?: number;
  endLine?: number;
  language?: string;
  title?: string;
  defaultOpen?: boolean;
}

export const SourcePreview = memo(function SourcePreview({
  filePath,
  startLine = 0,
  endLine = 0,
  language,
  title = "Source",
  defaultOpen = false,
}: SourcePreviewProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [lines, setLines] = useState<string[]>([]);
  const [actualStartLine, setActualStartLine] = useState(1);
  const [detectedLanguage, setDetectedLanguage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { readSource } = usePyloid();
  const fetchedRef = useRef<string>("");

  const cacheKey = `${filePath}:${startLine}:${endLine}`;

  const fetchSource = useCallback(async () => {
    if (fetchedRef.current === cacheKey) return;
    fetchedRef.current = cacheKey;

    setLoading(true);
    setError(null);
    try {
      const result = await readSource(filePath, startLine, endLine);
      if (result.error) {
        setError(result.error);
      } else {
        setLines(result.lines);
        setActualStartLine(result.startLine);
        setDetectedLanguage(result.language);
      }
    } catch (err) {
      setError(String(err));
    } finally {
      setLoading(false);
    }
  }, [readSource, filePath, startLine, endLine, cacheKey]);

  // Fetch source when expanded
  useEffect(() => {
    if (isOpen && lines.length === 0 && !error) {
      fetchSource();
    }
  }, [isOpen, lines.length, error, fetchSource]);

  // Highlight code and split into lines
  const highlightedLines = useMemo(() => {
    if (lines.length === 0) return [];

    const code = lines.join("\n");
    const lang = language || detectedLanguage;

    try {
      let html: string;
      if (lang && hljs.getLanguage(lang)) {
        html = hljs.highlight(code, { language: lang }).value;
      } else {
        html = hljs.highlightAuto(code).value;
      }
      return html.split("\n");
    } catch {
      return lines.map(
        (l) => l.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      );
    }
  }, [lines, language, detectedLanguage]);

  const lineCount = startLine > 0 && endLine > 0 ? `${endLine - startLine + 1} lines` : "";

  return (
    <div className="mt-1.5">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-300 w-full text-left group"
      >
        <svg
          className={`w-3 h-3 transition-transform shrink-0 ${isOpen ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
        </svg>
        <svg
          className="w-3 h-3 shrink-0 opacity-50 group-hover:opacity-75"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4"
          />
        </svg>
        <span>{title}</span>
        {lineCount && <span className="text-gray-600 ml-1">({lineCount})</span>}
      </button>

      {isOpen && (
        <div className="mt-1 rounded border border-gray-700 overflow-hidden">
          {loading && (
            <div className="flex items-center justify-center py-4 bg-gray-900">
              <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
            </div>
          )}

          {error && (
            <div className="px-3 py-2 bg-gray-900 text-red-400 text-xs">
              {error}
            </div>
          )}

          {!loading && !error && highlightedLines.length > 0 && (
            <div className="overflow-x-auto bg-gray-900 text-xs leading-relaxed">
              <table className="border-collapse">
                <tbody>
                  {highlightedLines.map((html, idx) => (
                    <tr key={idx} className="hover:bg-gray-800/50">
                      <td className="select-none text-right pr-3 pl-2 text-gray-600 border-r border-gray-800 whitespace-nowrap align-top font-mono leading-relaxed">
                        {actualStartLine + idx}
                      </td>
                      <td
                        className="pl-3 pr-3 whitespace-pre font-mono text-gray-300 align-top leading-relaxed"
                        dangerouslySetInnerHTML={{ __html: html || "&nbsp;" }}
                      />
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
});
