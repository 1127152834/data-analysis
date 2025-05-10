import type { EvaluationTaskItem } from '@/api/evaluations';
import { AutoErrorMessagePopper } from '@/components/cells/error-message';
import { DocumentPreviewDialog } from '@/components/document-viewer';
import type { CellContext } from '@tanstack/react-table';
import { CircleCheckIcon, CircleDashedIcon, CircleXIcon, Loader2Icon } from 'lucide-react';
import { useMemo } from 'react';
import wcwidth from 'wcwidth';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogTitle, DialogHeader, DialogTrigger } from '@/components/ui/dialog';
import * as React from 'react';

// eslint-disable-next-line react/display-name
export const documentCell = (title: string, trimLength = 50, mime = 'text/markdown') => (context: CellContext<any, string | undefined | null>) => {
  const content = context.getValue();

  const splitIndex = useMemo(() => {
    if (!content) {
      return -1;
    }

    let n = 0;

    for (let i = 0; i < content.length; i++) {
      if (n < trimLength) {
        n += wcwidth(content[i]);
      } else {
        return i;
      }
    }

    return -1;
  }, [content, trimLength]);

  if (!content) {
    return '--';
  }

  if (splitIndex < 0) {
    return content;
  }

  return (
    <DocumentPreviewDialog
      title={title}
      name={content.slice(0, splitIndex) + '...'}
      mime={mime}
      content={content}
    />
  );
};

export const textChunksArrayCell = (context: CellContext<any, string[] | undefined | null>) => {
  const value = context.getValue();
  if (!value?.length) {
    return null;
  }
  
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="link" className="p-0 h-auto">
          {value.length} 个片段
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-screen-lg">
        <DialogHeader>
          <DialogTitle>检索上下文片段</DialogTitle>
        </DialogHeader>
        <div className="max-h-[70vh] overflow-auto space-y-2">
          {value?.map((chunk: any, i: number) => (
            <div key={i} className="p-4 border rounded-md">
              <div className="text-sm text-muted-foreground mb-1">片段 #{i + 1}</div>
              <div className="whitespace-pre-wrap break-words">{chunk.text}</div>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
};

export const evaluationTaskStatusCell = (context: CellContext<EvaluationTaskItem, EvaluationTaskItem['status']>) => {
  const value = context.getValue();
  switch (value) {
    case 'done':
      return <Badge variant="secondary">完成</Badge>;
    case 'not_start':
      return <Badge variant="outline">未开始</Badge>;
    case 'error':
      return <Badge variant="destructive">错误</Badge>;
    case 'evaluating':
      return <Badge>进行中</Badge>;
    default:
      return value;
  }
};

function StatusCell ({ row }: { row: EvaluationTaskItem }) {
  const { status, error_msg } = row;
  return (
    <span className="inline-flex gap-1">
      {status === 'not_start' && <CircleDashedIcon className="text-muted-foreground flex-shrink-0 size-4" />}
      {status === 'cancel' && <CircleXIcon className="text-muted-foreground flex-shrink-0 size-4" />}
      {status === 'evaluating' && <Loader2Icon className="text-info flex-shrink-0 size-4 animate-spin repeat-infinite" />}
      {status === 'done' && <CircleCheckIcon className="text-success flex-shrink-0 size-4" />}
      {status === 'error' && <CircleXIcon className="text-destructive flex-shrink-0 size-4" />}
      <span className="text-accent-foreground">
        {status === 'not_start' ? '未开始' : status === 'evaluating' ? '进行中' : status === 'done' ? '完成' : status === 'cancel' ? '已取消' : '错误:'}
      </span>
      {status === 'error' && <AutoErrorMessagePopper trimLength={28}>{error_msg}</AutoErrorMessagePopper>}
    </span>
  );
}
