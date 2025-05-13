'use client';

import { useState } from 'react';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { Pagination, PaginationContent, PaginationItem, PaginationLink, PaginationNext, PaginationPrevious } from '@/components/ui/pagination';
import { Button } from '@/components/ui/button';
import { Download, Maximize2, Minimize2 } from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { SqlDisplay } from './SqlDisplay';
import { QueryResultExport } from './QueryResultExport';

interface DatabaseQueryResultProps {
  query: string;
  result: {
    columns: string[];
    rows: Record<string, any>[];
    totalRows: number;
    executionTimeMs: number;
  };
  connectionName?: string;
  databaseType?: string;
  error?: string;
  className?: string;
}

export function DatabaseQueryResult({
  query,
  result,
  connectionName,
  databaseType,
  error,
  className,
}: DatabaseQueryResultProps) {
  const [page, setPage] = useState(1);
  const [expanded, setExpanded] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  
  const rowsPerPage = 10;
  const totalPages = Math.ceil(result.rows.length / rowsPerPage);
  const startRow = (page - 1) * rowsPerPage;
  const endRow = Math.min(startRow + rowsPerPage, result.rows.length);
  const currentRows = result.rows.slice(startRow, endRow);
  
  const toggleExpand = () => {
    setExpanded(!expanded);
  };

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen);
  };

  const renderTable = () => (
    <>
      <div className="flex justify-between items-center mb-2">
        <div className="text-sm text-muted-foreground">
          {result.totalRows} rows · {result.executionTimeMs}ms
          {connectionName && databaseType && (
            <span> · {connectionName} ({databaseType})</span>
          )}
        </div>
        <div className="flex gap-2">
          <QueryResultExport data={result.rows} fileName="query_result" />
          <Button
            variant="ghost"
            size="sm"
            onClick={toggleExpand}
            className="h-8 w-8 p-0"
          >
            {expanded ? <Minimize2 className="h-4 w-4" /> : <Maximize2 className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      <SqlDisplay sql={query} databaseType={databaseType} />
      
      <ScrollArea className={`w-full ${expanded ? 'h-[500px]' : 'h-[300px]'}`}>
        <div className="min-w-full">
          <Table>
            <TableHeader>
              <TableRow>
                {result.columns.map((column) => (
                  <TableHead key={column}>{column}</TableHead>
                ))}
              </TableRow>
            </TableHeader>
            <TableBody>
              {currentRows.map((row, rowIndex) => (
                <TableRow key={rowIndex}>
                  {result.columns.map((column) => (
                    <TableCell key={`${rowIndex}-${column}`}>
                      {renderCellValue(row[column])}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </ScrollArea>
      
      {totalPages > 1 && (
        <Pagination className="mt-2">
          <PaginationContent>
            <PaginationItem>
              <PaginationPrevious 
                onClick={() => page > 1 && setPage(Math.max(1, page - 1))}
                aria-disabled={page === 1}
                className={page === 1 ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
            {renderPaginationItems()}
            <PaginationItem>
              <PaginationNext 
                onClick={() => page < totalPages && setPage(Math.min(totalPages, page + 1))}
                aria-disabled={page === totalPages}
                className={page === totalPages ? "pointer-events-none opacity-50" : ""}
              />
            </PaginationItem>
          </PaginationContent>
        </Pagination>
      )}
    </>
  );

  const renderPaginationItems = () => {
    // Logic to limit pagination items for large result sets
    const maxItems = 5;
    let startPage = Math.max(1, page - Math.floor(maxItems / 2));
    const endPage = Math.min(startPage + maxItems - 1, totalPages);
    
    if (endPage - startPage + 1 < maxItems) {
      startPage = Math.max(1, endPage - maxItems + 1);
    }
    
    const items = [];
    for (let i = startPage; i <= endPage; i++) {
      items.push(
        <PaginationItem key={i}>
          <PaginationLink 
            onClick={() => setPage(i)}
            isActive={page === i}
          >
            {i}
          </PaginationLink>
        </PaginationItem>
      );
    }
    return items;
  };

  const renderCellValue = (value: any) => {
    if (value === null || value === undefined) {
      return <span className="text-muted-foreground italic">NULL</span>;
    }
    
    if (typeof value === 'object') {
      try {
        return <span className="font-mono text-xs">{JSON.stringify(value)}</span>;
      } catch {
        return <span className="font-mono text-xs">[Object]</span>;
      }
    }
    
    return String(value);
  };
  
  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle>查询错误</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-destructive">{error}</div>
          <SqlDisplay sql={query} databaseType={databaseType} />
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card className={className}>
        <CardHeader className="pb-3">
          <CardTitle className="text-lg flex items-center justify-between">
            数据库查询结果
            <Button variant="ghost" size="sm" onClick={toggleFullscreen} className="h-8 w-8 p-0">
              <Maximize2 className="h-4 w-4" />
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>{renderTable()}</CardContent>
      </Card>

      <Dialog open={isFullscreen} onOpenChange={setIsFullscreen}>
        <DialogContent className="max-w-[90vw] w-full max-h-[90vh]">
          <DialogHeader>
            <DialogTitle>数据库查询结果</DialogTitle>
          </DialogHeader>
          <div className="overflow-auto">{renderTable()}</div>
        </DialogContent>
      </Dialog>
    </>
  );
} 