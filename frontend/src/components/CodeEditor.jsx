import React, { useRef, useEffect, useCallback } from 'react';
import Editor from '@monaco-editor/react';

// Decoration type constants
const HIGHLIGHT_LINE = 'highlight-line';
const ERROR_LINE = 'error-line';

export default function CodeEditor({
  code,
  onChange,
  selectedLine,
  errorLine,
  readOnly,
}) {
  const editorRef = useRef(null);
  const decorationsRef = useRef([]);

  const handleMount = useCallback((editor) => {
    editorRef.current = editor;
  }, []);

  // Update decorations when selectedLine or errorLine changes.
  // Uses editor.deltaDecorations to avoid recreating the editor.
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor) return;

    const newDecorations = [];

    if (selectedLine) {
      newDecorations.push({
        range: {
          startLineNumber: selectedLine,
          startColumn: 1,
          endLineNumber: selectedLine,
          endColumn: 1,
        },
        options: {
          isWholeLine: true,
          className: 'selected-line-highlight',
          glyphMarginClassName: 'selected-line-glyph',
          overviewRuler: { color: '#3b82f6', position: 2 },
        },
      });
    }

    if (errorLine && errorLine !== selectedLine) {
      newDecorations.push({
        range: {
          startLineNumber: errorLine,
          startColumn: 1,
          endLineNumber: errorLine,
          endColumn: 1,
        },
        options: {
          isWholeLine: true,
          className: 'error-line-highlight',
          glyphMarginClassName: 'error-line-glyph',
          overviewRuler: { color: '#ef4444', position: 3 },
        },
      });
    }

    decorationsRef.current = editor.deltaDecorations(
      decorationsRef.current,
      newDecorations
    );
  }, [selectedLine, errorLine]);

  // Reveal the selected line in the editor
  useEffect(() => {
    const editor = editorRef.current;
    if (!editor || !selectedLine) return;
    editor.revealLineInCenter(selectedLine);
  }, [selectedLine]);

  return (
    <div className="h-full flex flex-col">
      <div className="px-3 py-1 text-xs text-gray-500 bg-gray-900 border-b border-gray-800">
        Python Code
      </div>
      <div className="flex-1">
        <Editor
          height="100%"
          language="python"
          theme="vs-dark"
          value={code}
          onChange={(value) => onChange(value || '')}
          onMount={handleMount}
          options={{
            readOnly,
            minimap: { enabled: false },
            fontSize: 14,
            lineNumbers: 'on',
            renderLineHighlight: 'none',
            scrollBeyondLastLine: false,
            automaticLayout: true,
            padding: { top: 8 },
            glyphMargin: true,
            overviewRulerBorder: false,
            overviewRulerLanes: 2,
          }}
          loading={
            <div className="flex items-center justify-center h-full text-gray-500">
              Loading editor...
            </div>
          }
        />
      </div>
      <style>{`
        .selected-line-highlight { background: rgba(59, 130, 246, 0.15); }
        .selected-line-glyph { background: #3b82f6; width: 4px !important; margin-left: 3px; border-radius: 2px; }
        .error-line-highlight { background: rgba(239, 68, 68, 0.2); }
        .error-line-glyph { background: #ef4444; width: 4px !important; margin-left: 3px; border-radius: 2px; }
      `}</style>
    </div>
  );
}
