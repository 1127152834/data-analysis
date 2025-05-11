import React from 'react';
import { unified } from 'unified';
import remarkParse from 'remark-parse';
import remarkGfm from 'remark-gfm';
import remarkRehype from 'remark-rehype';
import rehypeReact from 'rehype-react';
import rehypeHighlight from 'rehype-highlight';
import * as jsxRuntime from 'react/jsx-runtime';

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  // 创建Markdown处理流程
  const processor = unified()
    .use(remarkParse) // 解析Markdown文本
    .use(remarkGfm) // 支持GFM (GitHub Flavored Markdown)
    .use(remarkRehype) // 将Markdown AST转换为HTML AST
    .use(rehypeHighlight) // 代码高亮
    .use(rehypeReact, { 
      jsx: (jsxRuntime as any).jsx,
      jsxs: (jsxRuntime as any).jsxs,
      Fragment: (jsxRuntime as any).Fragment
    }); // 将HTML AST转换为React元素

  // 处理Markdown内容
  const result = processor.processSync(content).result;

  return (
    <div className={`markdown-renderer prose dark:prose-invert ${className || ''}`}>
      {result}
    </div>
  );
} 