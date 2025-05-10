'use client';

import { type ChatEngine, createChatEngine, deleteChatEngine, listChatEngines } from '@/api/chat-engines';
import { actions } from '@/components/cells/actions';
import { boolean } from '@/components/cells/boolean';
import { datetime } from '@/components/cells/datetime';
import { mono } from '@/components/cells/mono';
import { DataTableRemote } from '@/components/data-table-remote';
import { useBootstrapStatus } from '@/components/system/BootstrapStatusProvider';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import type { ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import { AlertTriangleIcon, CopyIcon, TrashIcon } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';

const helper = createColumnHelper<ChatEngine>();

const columns = [
  helper.accessor('id', { 
    header: 'ID',
    cell: mono 
  }),
  helper.accessor('name', { 
    header: '名称',
    cell: context => <NameLink chatEngine={context.row.original} /> 
  }),
  helper.accessor('created_at', { 
    header: '创建时间',
    cell: datetime 
  }),
  helper.accessor('updated_at', { 
    header: '更新时间',
    cell: datetime 
  }),
  helper.accessor('is_default', { 
    header: '是否默认',
    cell: boolean 
  }),
  helper.display({
    header: '操作',
    cell: actions((chatEngine) => [
      {
        key: 'clone',
        action: async ({ startTransition, router }) => {
          const { name, llm_id, fast_llm_id, engine_options } = chatEngine;
          createChatEngine({
            name: `${name} 副本`, llm_id, fast_llm_id, engine_options,
          })
            .then(newEngine => {
              toast.success('聊天引擎克隆成功。');
              startTransition(() => {
                router.push(`/chat-engines/${newEngine.id}`);
              });
            });
        },
        icon: <CopyIcon className="size-3" />,
        title: '克隆',
      },
      {
        key: 'delete',
        action: async ({ table, setDropdownOpen }) => {
          await deleteChatEngine(chatEngine.id);
          table.reload?.();
          setDropdownOpen(false);
        },
        title: '删除',
        icon: <TrashIcon className="size-3" />,
        dangerous: {},
      },
    ]),
  }),
] as ColumnDef<ChatEngine>[];

export function ChatEnginesTable () {
  return (
    <DataTableRemote
      columns={columns}
      apiKey="api.chat-engines.list"
      api={listChatEngines}
      idColumn="id"
    />
  );
}

function NameLink ({ chatEngine }: { chatEngine: ChatEngine }) {
  const { need_migration } = useBootstrapStatus();

  const kbNotConfigured = !!need_migration.chat_engines_without_kb_configured?.includes(chatEngine.id);

  return (
    <Link
      className="underline font-mono"
      href={`/chat-engines/${chatEngine.id}`}
    >
      {kbNotConfigured && <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <AlertTriangleIcon className="text-warning inline-flex mr-1 size-3" />
          </TooltipTrigger>
          <TooltipContent className="text-xs" align="start">
            知识库未配置。
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>}
      {chatEngine.name}
    </Link>
  );
}
