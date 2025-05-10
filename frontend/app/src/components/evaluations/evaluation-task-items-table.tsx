'use client';

import { type EvaluationTaskItem, listEvaluationTaskItems } from '@/api/evaluations';
import { datetime } from '@/components/cells/datetime';
import { metadataCell } from '@/components/cells/metadata';
import { mono } from '@/components/cells/mono';
import { percent } from '@/components/cells/percent';
import { DataTableRemote } from '@/components/data-table-remote';
import { documentCell, evaluationTaskStatusCell, textChunksArrayCell } from '@/components/evaluations/cells';
import { type KeywordFilter, KeywordFilterToolbar } from '@/components/evaluations/keyword-filter-toolbar';
import type { ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import { useState } from 'react';

const helper = createColumnHelper<EvaluationTaskItem>();

const columns = [
  helper.accessor('id', { header: 'ID', cell: mono }),
  helper.accessor('status', { header: '状态', cell: evaluationTaskStatusCell, meta: { colSpan: context => context.row.original.status === 'error' ? 3 : 1 } }),
  helper.accessor('semantic_similarity', {
    header: '语义相似度',
    cell: context => percent(context, {
      colorStops: [
        { checkpoint: 0, color: 'hsl(var(--destructive))' },
        { checkpoint: 1 - 0.618, color: 'hsl(var(--destructive))' },
        { checkpoint: 0.5, color: 'hsl(var(--warning))' },
        { checkpoint: 0.618, color: 'hsl(var(--success))' },
        { checkpoint: 1, color: 'hsl(var(--success))' },
      ],
    }),
    meta: { colSpan: context => context.row.original.status === 'error' ? 0 : 1 }
  }),
  helper.accessor('factual_correctness', {
    header: '事实准确性',
    cell: context => percent(context, {
      colorStops: [
        { checkpoint: 0, color: 'hsl(var(--destructive))' },
        { checkpoint: 1 - 0.618, color: 'hsl(var(--destructive))' },
        { checkpoint: 0.5, color: 'hsl(var(--warning))' },
        { checkpoint: 0.618, color: 'hsl(var(--success))' },
        { checkpoint: 1, color: 'hsl(var(--success))' },
      ],
    }),
    meta: { colSpan: context => context.row.original.status === 'error' ? 0 : 1 }
  }),
  helper.accessor('query', { header: '查询', cell: documentCell('查询') }),
  helper.accessor('chat_engine', { header: '聊天引擎' }),
  helper.accessor('reference', { header: '参考', cell: documentCell('参考') }),
  helper.accessor('response', { header: '响应', cell: documentCell('响应') }),
  helper.accessor('retrieved_contexts', { header: '检索上下文', cell: textChunksArrayCell }),
  helper.accessor('extra', { header: '额外信息', cell: metadataCell }),
  helper.accessor('created_at', { header: '创建时间', cell: datetime }),
  helper.accessor('updated_at', { header: '更新时间', cell: datetime }),
] as ColumnDef<EvaluationTaskItem>[];

export function EvaluationTaskItemsTable ({ evaluationTaskId }: { evaluationTaskId: number }) {
  const [filter, setFilter] = useState<KeywordFilter>({});
  
  return (
    <DataTableRemote
      columns={columns}
      toolbar={() => (
        <KeywordFilterToolbar onFilterChange={setFilter} placeholder="搜索查询或响应" />
      )}
      apiKey={`api.evaluation.tasks.${evaluationTaskId}.items.list`}
      api={(page) => listEvaluationTaskItems(evaluationTaskId, { ...page, ...filter })}
      apiDeps={[filter.keyword]}
      idColumn="id"
    />
  );
}
