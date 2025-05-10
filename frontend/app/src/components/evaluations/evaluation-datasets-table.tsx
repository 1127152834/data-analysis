'use client';

import { deleteEvaluationDataset, type EvaluationDataset, listEvaluationDatasets } from '@/api/evaluations';
import { actions } from '@/components/cells/actions';
import { datetime } from '@/components/cells/datetime';
import { link } from '@/components/cells/link';
import { mono } from '@/components/cells/mono';
import { DataTableRemote } from '@/components/data-table-remote';
import { mutateEvaluationDatasets } from '@/components/evaluations/hooks';
import { type KeywordFilter, KeywordFilterToolbar } from '@/components/evaluations/keyword-filter-toolbar';
import type { ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import { useState } from 'react';

const helper = createColumnHelper<EvaluationDataset>();

const columns = [
  helper.accessor('id', { header: 'ID', cell: mono }),
  helper.accessor('name', { header: '名称', cell: link({ text: row => row.name, url: row => `/evaluation/datasets/${row.id}` }) }),
  helper.accessor('user_id', { header: '用户ID' }),
  helper.accessor('created_at', { header: '创建时间', cell: datetime }),
  helper.accessor('updated_at', { header: '更新时间', cell: datetime }),
  helper.display({
    id: 'op',
    header: '操作',
    cell: actions(row => [
      {
        key: 'update',
        title: '更新',
        action: context => {
          context.startTransition(() => {
            context.router.push(`/evaluation/datasets/${row.id}`);
          });
        },
      },
      {
        key: 'delete',
        title: '删除',
        dangerous: {},
        action: async context => {
          await deleteEvaluationDataset(row.id);
          context.startTransition(() => {
            context.router.refresh();
            void mutateEvaluationDatasets();
          });
          context.setDropdownOpen(false);
        },
      },
    ]),
  }),
] as ColumnDef<EvaluationDataset>[];

export function EvaluationDatasetsTable () {
  const [filter, setFilter] = useState<KeywordFilter>({});
  return (
    <DataTableRemote
      toolbar={() => (
        <KeywordFilterToolbar onFilterChange={setFilter} />
      )}
      columns={columns}
      apiKey="api.evaluation.datasets.list"
      api={page => listEvaluationDatasets({ ...page, ...filter })}
      apiDeps={[filter.keyword]}
      idColumn="id"
    />
  );
}
