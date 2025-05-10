'use client';

import { setDefault } from '@/api/commons';
import { type EmbeddingModel, listEmbeddingModels } from '@/api/embedding-models';
import { actions } from '@/components/cells/actions';
import { mono } from '@/components/cells/mono';
import { DataTableRemote } from '@/components/data-table-remote';
import { Badge } from '@/components/ui/badge';
import { getErrorMessage } from '@/lib/errors';
import type { ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import Link from 'next/link';
import { toast } from 'sonner';

export function EmbeddingModelsTable () {
  return (
    <DataTableRemote
      columns={columns}
      apiKey="api.embedding-models.list"
      api={listEmbeddingModels}
      idColumn="id"
    />
  );
}

const helper = createColumnHelper<EmbeddingModel>();
const columns: ColumnDef<EmbeddingModel, any>[] = [
  helper.accessor('id', {
    header: 'ID',
    cell: ({ row }) => row.original.id
  }),
  helper.accessor('name', {
    header: '名称',
    cell: ({ row }) => {
      const { id, name, is_default } = row.original;
      return (
        <Link className="flex gap-1 items-center underline" href={`/embedding-models/${id}`}>
          {is_default && <Badge>默认</Badge>}
          {name}
        </Link>
      );
    },
  }),
  helper.display({
    header: '提供商 / 模型',
    cell: ({ row }) => {
      const { model, provider } = row.original;
      return (
        <>
          <strong>{provider}</strong>/<span>{model}</span>
        </>
      );
    },
  }),
  helper.accessor('vector_dimension', { 
    header: '向量维度',
    cell: mono 
  }),
  helper.display({
    id: 'Operations',
    header: '操作',
    cell: actions(row => ([
      {
        key: 'set-default',
        title: '设为默认',
        disabled: row.is_default,
        action: async (context) => {
          try {
            await setDefault('embedding-models', row.id);
            context.table.reload?.();
            context.startTransition(() => {
              context.router.refresh();
            });
            context.setDropdownOpen(false);
            toast.success(`成功将嵌入模型 ${row.name} 设为默认。`);
          } catch (e) {
            toast.error(`将嵌入模型 ${row.name} 设为默认失败。`, {
              description: getErrorMessage(e),
            });
            throw e;
          }
        },
      },
    ])),
  }),
];
