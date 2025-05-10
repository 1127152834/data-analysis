'use client';

import { type Chat, deleteChat, listChats } from '@/api/chats';
import { actions } from '@/components/cells/actions';
import { datetime } from '@/components/cells/datetime';
import { link } from '@/components/cells/link';
import { metadataCell } from '@/components/cells/metadata';
import { DataTableRemote } from '@/components/data-table-remote';
import { createColumnHelper } from '@tanstack/table-core';
import { Trash2Icon } from 'lucide-react';

export function ChatsTable () {
  return (
    <DataTableRemote
      idColumn="id"
      apiKey="api.chats.list"
      api={listChats}
      columns={columns as any}
    />
  );
}

const helper = createColumnHelper<Chat>();

const columns = [
  helper.accessor('title', {
    cell: link({ url: chat => `/c/${chat.id}` }),
    header: '标题',
  }),
  helper.accessor('origin', {
    header: '来源',
  }),
  helper.accessor('created_at', { 
    cell: datetime,
    header: '创建时间',
  }),
  helper.accessor('engine_id', {
    header: '引擎ID',
  }),
  helper.accessor('engine_options', { 
    cell: metadataCell,
    header: '引擎选项',
  }),
  helper.display({
    header: '操作',
    cell: actions(chat => [
      {
        key: 'delete',
        title: '删除',
        icon: <Trash2Icon className="size-3" />,
        dangerous: {
          dialogTitle: '确定要删除此聊天？',
          dialogDescription: '此操作无法撤销。',
        },
        action: async ({ table }) => {
          await deleteChat(chat.id);
          table.reload?.();
        },
      },
    ]),
  }),
];
