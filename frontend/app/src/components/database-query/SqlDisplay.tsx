'use client';

import { useState } from 'react';
import { Copy, Check } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

interface SqlDisplayProps {
  sql: string;
  databaseType?: string;
  className?: string;
  showCopy?: boolean;
  maxHeight?: string;
}

export function SqlDisplay({
  sql,
  databaseType,
  className,
  showCopy = true,
  maxHeight = '200px',
}: SqlDisplayProps) {
  const [copied, setCopied] = useState(false);

  const copyToClipboard = () => {
    navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Simple syntax highlighting for SQL
  const formattedSql = () => {
    if (!sql) return '';

    // Format SQL with simple syntax highlighting
    // This is a basic implementation - for production, consider using a dedicated syntax highlighter library
    const keywords = [
      'SELECT', 'FROM', 'WHERE', 'JOIN', 'LEFT JOIN', 'RIGHT JOIN', 'INNER JOIN',
      'GROUP BY', 'ORDER BY', 'HAVING', 'LIMIT', 'OFFSET', 'INSERT', 'UPDATE',
      'DELETE', 'CREATE', 'ALTER', 'DROP', 'AS', 'AND', 'OR', 'NOT', 'IN',
      'BETWEEN', 'LIKE', 'IS NULL', 'IS NOT NULL', 'ASC', 'DESC', 'DISTINCT',
      'CASE', 'WHEN', 'THEN', 'ELSE', 'END'
    ];

    // Replace SQL keywords with styled spans
    let highlighted = sql;
    keywords.forEach(keyword => {
      const regex = new RegExp(`\\b${keyword}\\b`, 'gi');
      highlighted = highlighted.replace(regex, match => 
        `<span class="text-blue-500 font-semibold">${match}</span>`
      );
    });

    // Highlight strings
    highlighted = highlighted.replace(/'([^']*)'/g, 
      "<span class=\"text-green-600\">'$1'</span>"
    );

    // Highlight numbers
    highlighted = highlighted.replace(/\b(\d+)\b/g, 
      "<span class=\"text-amber-600\">$1</span>"
    );

    // Replace newlines with <br>
    highlighted = highlighted.replace(/\n/g, '<br>');

    return highlighted;
  };

  return (
    <Card className={cn("my-2 overflow-hidden", className)}>
      <CardContent className="p-2 relative">
        <div
          className="font-mono text-sm whitespace-pre-wrap overflow-auto p-2"
          style={{ maxHeight }}
          dangerouslySetInnerHTML={{ __html: formattedSql() }}
        />
        {showCopy && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute top-2 right-2 h-8 w-8 p-0"
            onClick={copyToClipboard}
          >
            {copied ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
          </Button>
        )}
        {databaseType && (
          <div className="text-xs text-muted-foreground mt-2">
            {databaseType} SQL
          </div>
        )}
      </CardContent>
    </Card>
  );
} 