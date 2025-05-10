'use client';

import { actions } from '@/components/cells/actions';
import { type DatasourceKgIndexError, type DatasourceVectorIndexError } from '@/api/datasources';
import { listKnowledgeBaseKgIndexErrors, listKnowledgeBaseVectorIndexErrors, rebuildKBDocumentIndex, retryKnowledgeBaseAllFailedTasks } from '@/api/knowledge-base';
import { errorMessageCell } from '@/components/cells/error-message';
import { link } from '@/components/cells/link';
import { IndexProgressChart, IndexProgressChartPlaceholder } from '@/components/charts/IndexProgressChart';
import { TotalCard } from '@/components/charts/TotalCard';
import { DangerousActionButton } from '@/components/dangerous-action-button';
import { DataTableRemote } from '@/components/data-table-remote';
import { useKnowledgeBaseIndexProgress } from '@/components/knowledge-base/hooks';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import type { ColumnDef } from '@tanstack/react-table';
import { createColumnHelper } from '@tanstack/table-core';
import { ArrowRightIcon, DownloadIcon, FileTextIcon, PuzzleIcon, RouteIcon, WrenchIcon } from 'lucide-react';
import Link from 'next/link';
import { toast } from 'sonner';
import { getErrorMessage } from '@/lib/errors';

export function KnowledgeBaseIndexProgress ({ id }: { id: number }) {
  const { progress, isLoading } = useKnowledgeBaseIndexProgress(id);

  return (
    <>
      <div className="grid sm:grid-cols-2 md:grid-cols-4 gap-4">
        <TotalCard
          title="文档"
          icon={<FileTextIcon className="h-4 w-4 text-muted-foreground" />}
          total={progress?.documents.total}
          isLoading={isLoading}
        >
          <Link className="flex gap-2 items-center" href={`/knowledge-bases/${id}`}>所有文档 <ArrowRightIcon className="size-3" /></Link>
        </TotalCard>
        <TotalCard
          title="块"
          icon={<PuzzleIcon className="h-4 w-4 text-muted-foreground" />}
          total={progress?.chunks.total}
          isLoading={isLoading}
        />
        <TotalCard
          title="实体"
          icon={<RouteIcon className="h-4 w-4 text-muted-foreground" />}
          total={progress?.entities?.total || null}
          isLoading={isLoading}
        />
        <TotalCard
          title="关系"
          icon={<RouteIcon className="h-4 w-4 text-muted-foreground" />}
          total={progress?.relationships?.total || null}
          isLoading={isLoading}
        />
      </div>
      <div className="mt-4 grid grid-cols-2 gap-4">
        {progress ? <IndexProgressChart title="向量索引" data={progress.vector_index} label="文档总数" /> : <IndexProgressChartPlaceholder title="向量索引" label="文档总数" />}
        {progress?.kg_index ? <IndexProgressChart title="知识图谱索引" data={progress.kg_index} label="块总数" /> : <IndexProgressChartPlaceholder title="知识图谱索引" label="块总数" />}
      </div>
      <KnowledgeBaseIndexErrors id={id} />
    </>
  );
}

export function KnowledgeBaseIndexErrors ({ id }: { id: number }) {
  const { progress, mutate } = useKnowledgeBaseIndexProgress(id);

  if (!progress) {
    return null;
  }
  const showVectorIndexErrors = !!progress.vector_index.failed;
  const showKgIndexErrors = !!progress.kg_index?.failed;

  if (!showVectorIndexErrors && !showKgIndexErrors) {
    return null;
  }

  return (
    <section className="space-y-4">
      <h3>失败任务</h3>
      <Tabs defaultValue={showVectorIndexErrors ? 'vector-index-errors' : 'kg-index-errors'}>
        <div className="flex items-center">
          <TabsList>
            <TabsTrigger value="vector-index-errors">
              向量索引
            </TabsTrigger>
            <TabsTrigger value="kg-index-errors">
              知识图谱索引
            </TabsTrigger>
          </TabsList>
          <DangerousActionButton
            className="ml-auto"
            action={async () => {
              await retryKnowledgeBaseAllFailedTasks(id);
              await mutate(undefined, { revalidate: true });
            }}
            dialogTitle="重试失败任务"
            dialogDescription="您确定要重试所有失败的任务吗？"
          >
            重试失败任务
          </DangerousActionButton>

        </div>
        <TabsContent value="vector-index-errors">
          <KBVectorIndexErrorsTable kb_id={id} />
        </TabsContent>
        <TabsContent value="kg-index-errors">
          <KBKGIndexErrorsTable kb_id={id} />
        </TabsContent>
      </Tabs>
    </section>
  );
}

function KBVectorIndexErrorsTable ({ kb_id }: { kb_id: number }) {
  return (
    <DataTableRemote<DatasourceVectorIndexError, any>
      api={(params) => listKnowledgeBaseVectorIndexErrors(kb_id, params)}
      apiKey={`datasources.${kb_id}.vector-index-errors`}
      columns={getVectorIndexErrorsColumns(kb_id)}
      idColumn="document_id"
    />
  );
}

function KBKGIndexErrorsTable ({ kb_id }: { kb_id: number }) {
  return (
    <DataTableRemote<DatasourceKgIndexError, any>
      api={(params) => listKnowledgeBaseKgIndexErrors(kb_id, params)}
      apiKey={`datasources.${kb_id}.kg-index-errors`}
      columns={getKgIndexErrorsColumns(kb_id)}
      idColumn="chunk_id"
    />
  );
}

const vectorIndexErrorsHelper = createColumnHelper<DatasourceVectorIndexError>();
const getVectorIndexErrorsColumns = (kb_id: number): ColumnDef<DatasourceVectorIndexError, any>[] => {
  return [
    vectorIndexErrorsHelper.display({
      header: 'Document', cell: ({ row }) => (
        <>
          {row.original.document_name}
          {' '}
          <span className="text-muted-foreground">#{row.original.document_id}</span>
        </>
      ),
    }),
    vectorIndexErrorsHelper.accessor('source_uri', {
      header: '源 URI',
      cell: link({ icon: <DownloadIcon className="size-3" />, truncate: true })
    }),
    vectorIndexErrorsHelper.accessor('error', {
      header: '错误信息',
      cell: errorMessageCell(),
    }),
    vectorIndexErrorsHelper.display({
      id: 'op',
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
              await rebuildKBDocumentIndex(kb_id, row.document_id);
              context.table.reload?.();
              context.startTransition(() => {
                context.router.refresh();
              });
              context.setDropdownOpen(false);
              toast.success(`Successfully rebuild index for document "${row.document_name}"`);
            } catch (e) {
              toast.error(`Failed to rebuild index for document "${row.document_name}"`, {
                description: getErrorMessage(e),
              });
              return Promise.reject(e);
            }
          },
        },
      ]),
    }),
  ]
};

const kgIndexErrorsHelper = createColumnHelper<DatasourceKgIndexError>();
const getKgIndexErrorsColumns = (kb_id: number): ColumnDef<DatasourceKgIndexError, any>[] => {
  return [
    kgIndexErrorsHelper.display({
      header: '文档',
      cell: ({ row }) => (
      <>
        {row.original.document_name}
        {' '}
        <span className="text-muted-foreground">#{row.original.document_id}</span>
      </>
    ),
    }),
    kgIndexErrorsHelper.accessor('source_uri', {
      header: '源 URI',
      cell: link({ icon: <DownloadIcon className="size-3" />, truncate: true })
    }),
    kgIndexErrorsHelper.accessor('chunk_id', { header: '块 ID' }),
    kgIndexErrorsHelper.accessor('error', {
      header: '错误信息',
      cell: errorMessageCell(),
    }),
    kgIndexErrorsHelper.display({
      id: 'op',
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
              await rebuildKBDocumentIndex(kb_id, row.document_id);
              context.table.reload?.();
              context.startTransition(() => {
                context.router.refresh();
              });
              context.setDropdownOpen(false);
              toast.success(`Successfully rebuild knowledge graph index for document "${row.document_name}"`);
            } catch (e) {
              toast.error(`Failed to rebuild knowledge graph index for document "${row.document_name}"`, {
                description: getErrorMessage(e),
              });
              return Promise.reject(e);
            }
          },
        },
      ]),
    }),
  ]
};
