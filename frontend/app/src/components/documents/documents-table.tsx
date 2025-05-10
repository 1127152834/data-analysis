'use client';

import { link } from '@/components/cells/link';
import { type Document, listDocuments, type ListDocumentsTableFilters } from '@/api/documents';
import { deleteKnowledgeBaseDocument, rebuildKBDocumentIndex } from '@/api/knowledge-base';
import { actions } from '@/components/cells/actions';
import { datetime } from '@/components/cells/datetime';
import { mono } from '@/components/cells/mono';
import { DatasourceCell } from '@/components/cells/reference';
import { DataTableRemote } from '@/components/data-table-remote';
import { DocumentPreviewDialog } from '@/components/document-viewer';
import { DocumentsTableFilters } from '@/components/documents/documents-table-filters';
import { getErrorMessage } from '@/lib/errors';
import type { CellContext, ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import { TrashIcon, UploadIcon, BlocksIcon, WrenchIcon, DownloadIcon, FileDownIcon } from 'lucide-react';
import { useMemo, useState } from 'react';
import { toast } from 'sonner';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { parseHref } from '@/components/chat/utils';

const helper = createColumnHelper<Document>();

const truncateUrl = (url: string, maxLength: number = 30): string => {
  if (!url || url.length <= maxLength) return url;
  const start = url.substring(0, maxLength / 2);
  const end = url.substring(url.length - maxLength / 2);
  return `${start}...${end}`;
};

const href = (cell: CellContext<Document, string>) => {
  const url = cell.getValue();
  if (/^https?:\/\//.test(url)) {
    return <a className="underline" href={url} target="_blank">{url}</a>;
  } else if (url.startsWith('uploads/')) {
    return (
      <a className="underline" {...parseHref(cell.row.original)}>
        <FileDownIcon className="inline-flex size-4 mr-1 stroke-1" />
        {truncateUrl(url)}
      </a>
    );
  } else {
    return <span title={url}>{truncateUrl(url)}</span>;
  }
};


const getColumns = (kbId: number) => [
  helper.accessor('id', { header: "ID", cell: mono }),
  helper.display({
    id: 'name', 
    header: '名称',
    cell: ({ row }) =>
      <DocumentPreviewDialog
        title={row.original.name}
        name={row.original.name}
        mime={row.original.mime_type}
        content={row.original.content}
      />,
  }),
  helper.accessor('source_uri', {
    header: "来源地址",
    cell: href,
  }),
  helper.accessor('data_source', { header: "数据源", cell: ctx => <DatasourceCell {...ctx.getValue()} /> }),
  helper.accessor('updated_at', { header: "最近更新", cell: datetime }),
  helper.accessor('index_status', { header: "索引状态", cell: mono }),
  helper.display({
    id: 'op',
    header: '操作',
    cell: actions(row => [
      {
        type: 'label',
        title: '操作',
      },
      {
        key: 'rebuild-index',
        title: '重建索引',
        icon: <WrenchIcon className="size-3" />,
        action: async (context) => {
          try {
            await rebuildKBDocumentIndex(kbId, row.id);
            context.table.reload?.();
            context.startTransition(() => {
              context.router.refresh();
            });
            context.setDropdownOpen(false);
            toast.success(`已成功为文档 "${row.name}" 重建索引`);
          } catch (e) {
            toast.error(`为文档 "${row.name}" 重建索引失败`, {
              description: getErrorMessage(e),
            });
            return Promise.reject(e);
          }
        },
      },
      {
        key: 'view-chunks',
        title: '查看文本块',
        icon: <BlocksIcon className="size-3" />,
        action: async (context) => {
          context.router.push(`/knowledge-bases/${kbId}/documents/${row.id}/chunks`);
        },
      },
      {
        type: 'separator',
      },
      {
        key: 'delete-document',
        title: '删除',
        icon: <TrashIcon className="size-3" />,
        dangerous: {
          dialogTitle: `确定要删除文档 "${row.name}" 吗？`,
        },
        action: async (context) => {
          try {
            await deleteKnowledgeBaseDocument(kbId, row.id);
            context.table.reload?.();
            context.startTransition(() => {
              context.router.refresh();
            });
            context.setDropdownOpen(false);
            toast.success(`已成功删除文档 "${row.name}"`);
          } catch (e) {
            toast.error(`删除文档 "${row.name}" 失败`, {
              description: getErrorMessage(e),
            });
            return Promise.reject(e);
          }
        },
      },
    ]),
  }),
] as ColumnDef<Document>[];

export function DocumentsTable ({ knowledgeBaseId }: { knowledgeBaseId: number }) {
  const [filters, setFilters] = useState<ListDocumentsTableFilters>({});

  const columns = useMemo(() => {
    return [...getColumns(knowledgeBaseId)];
  }, [knowledgeBaseId]);

  return (
    <DataTableRemote
      toolbar={((table) => (
          <div className="py-1">
            <DocumentsTableFilters
              knowledgeBaseId={knowledgeBaseId}
              table={table}
              onFilterChange={setFilters}
            />
        </div>
      ))}
      columns={columns}
      apiKey={knowledgeBaseId != null ? `api.datasource.${knowledgeBaseId}.documents` : 'api.documents.list'}
      api={(params) => listDocuments({ ...params, ...filters, knowledge_base_id: knowledgeBaseId })}
      apiDeps={[filters]}
      idColumn="id"
    />
  );
}

