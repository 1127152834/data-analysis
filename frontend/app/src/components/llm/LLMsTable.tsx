'use client';

import { setDefault } from '@/api/commons';
import { deleteLlm, listLlms, type LLM } from '@/api/llms';
import { actions } from '@/components/cells/actions';
import { DataTableRemote } from '@/components/data-table-remote';
import { Badge } from '@/components/ui/badge';
import { getErrorMessage } from '@/lib/errors';
import type { ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import { TrashIcon } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

export function LLMsTable () {
  return (
    <DataTableRemote
      columns={columns}
      apiKey="api.llms.list"
      api={listLlms}
      idColumn="id"
    />
  );
}

const helper = createColumnHelper<LLM>();
const columns: ColumnDef<LLM, any>[] = [
  helper.accessor('id', {
    header: 'ID',
    cell: ({ row }) => row.original.id,
  }),
  helper.accessor('name', {
    header: '名称',
    cell: ({ row }) => {
      const { id, name, is_default } = row.original;
      return (
        <Link className="flex gap-1 items-center underline" href={`/llms/${id}`}>
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
            await setDefault('llms', row.id);
            context.table.reload?.();
            context.startTransition(() => {
              context.router.refresh();
            });
            context.setDropdownOpen(false);
            toast.success(`已成功将 ${row.name} 设为默认大语言模型。`);
          } catch (e) {
            toast.error(`将 ${row.name} 设为默认大语言模型失败。`, {
              description: getErrorMessage(e),
            });
            throw e;
          }
        },
      },
      {
        key: 'delete',
        action: async ({ table, setDropdownOpen }) => {
          await deleteLlm(row.id);
          table.reload?.();
          setDropdownOpen(false);
        },
        title: '删除',
        icon: <TrashIcon className="size-3" />,
        dangerous: {},
      },
    ])),
  }),
];
