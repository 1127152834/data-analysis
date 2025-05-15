'use client';

import { useState, useRef, useEffect } from 'react';
import type { editor } from 'monaco-editor';

interface MonacoEditorProps {
  value: string;
  language?: string;
  onChange?: (value: string) => void;
  height?: string;
  width?: string;
  options?: editor.IStandaloneEditorConstructionOptions;
}

export default function MonacoEditor({
  value,
  language = 'json',
  onChange,
  height = '400px',
  width = '100%',
  options = {},
}: MonacoEditorProps) {
  const editorRef = useRef<editor.IStandaloneCodeEditor | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [isEditorReady, setIsEditorReady] = useState(false);

  useEffect(() => {
    let monaco: typeof import('monaco-editor');

    const initMonaco = async () => {
      monaco = await import('monaco-editor');
      
      if (containerRef.current) {
        editorRef.current = monaco.editor.create(containerRef.current, {
          value,
          language,
          automaticLayout: true,
          minimap: { enabled: false },
          ...options,
        });

        editorRef.current.onDidChangeModelContent(() => {
          if (onChange && editorRef.current) {
            onChange(editorRef.current.getValue());
          }
        });

        setIsEditorReady(true);
      }
    };

    initMonaco();

    return () => {
      if (editorRef.current) {
        editorRef.current.dispose();
        editorRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (isEditorReady && editorRef.current && value !== editorRef.current.getValue()) {
      editorRef.current.setValue(value);
    }
  }, [value, isEditorReady]);

  return (
    <div 
      ref={containerRef} 
      style={{ 
        height, 
        width,
        border: '1px solid #ccc',
        borderRadius: '4px',
      }} 
    />
  );
} 